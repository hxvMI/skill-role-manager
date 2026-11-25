import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1]/'plugins/skill-role-manager/skills/manage-skills/scripts/manager.py'
spec = importlib.util.spec_from_file_location('manager',SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class ManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.target = self.base/'target'
        self.target.mkdir()
        self.source = self.make_package('sample')

    def make_package(self,name,version='1.0.0',permissions=None,dependencies=None):
        root = self.base/(name+'-'+version)
        root.mkdir(exist_ok=True)
        (root/'skills'/'hello').mkdir(parents=True,exist_ok=True)
        (root/'skills'/'hello'/'SKILL.md').write_text('---\nname: hello\ndescription: Test greeting workflow.\n---\nGreet the user.\n',encoding='utf-8')
        (root/'plugin.json').write_bytes(m.encoded({'$schema':'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json','name':name,'version':version,'description':'Test package'}))
        self.seal(root,permissions or [],dependencies or {})
        return root

    def seal(self,root,permissions=None,dependencies=None):
        plugin = json.loads((root/'plugin.json').read_bytes())
        old = json.loads((root/'manager.json').read_bytes()) if (root/'manager.json').exists() else {}
        hashes = {p.relative_to(root).as_posix():m.digest(p.read_bytes()) for p in root.rglob('*') if p.is_file() and p.name != 'manager.json'}
        (root/'manager.json').write_bytes(m.encoded({'schema_version':1,'id':plugin['name'],'version':plugin['version'],
            'permissions':permissions if permissions is not None else old.get('permissions',[]),
            'dependencies':dependencies if dependencies is not None else old.get('dependencies',{}),'files':hashes}))

    def install(self,source=None,grants=(),fault=None):
        source = source or self.source
        p,_ = m.plan(self.target,'register',source,grants=grants)
        return m.apply(self.target,'register',source,grants=grants,expected=p['plan_digest'],fault=fault)

    def test_N1_read_only_plan_and_validation(self):
        self.assertEqual(m.validate(self.source)['id'],'sample')
        p,_=m.plan(self.target,'register',self.source)
        self.assertFalse(p['noop'])
        self.assertEqual(list(self.target.iterdir()),[])

    def test_N2_digest_required_and_noop(self):
        with self.assertRaises(m.ManagerError): m.apply(self.target,'register',self.source,expected='bad')
        self.assertIsNone(m.catalog_bytes(self.target))
        self.install()
        self.assertTrue(self.install()['noop'])

    def test_N3_permissions_and_dependencies(self):
        self.seal(self.source,['local-code'],{'missing':'1.0.0'})
        with self.assertRaisesRegex(m.ManagerError,'permission'): m.plan(self.target,'register',self.source)
        with self.assertRaisesRegex(m.ManagerError,'dependency'): m.plan(self.target,'register',self.source,grants=['local-code'])

    def test_N4_update_unregister_rollback_preserve_unrelated(self):
        raw=m.encoded({'name':'existing','custom':True,'plugins':[{'name':'unrelated','source':'./elsewhere'}]})
        m.atomic(m.within(self.target,m.CATALOG),raw)
        self.install()
        update=self.make_package('sample','2.0.0')
        tx=self.install(update)['transaction']
        self.assertEqual(m.catalog(m.catalog_bytes(self.target))['plugins'][0]['name'],'unrelated')
        m.recover(self.target,tx)
        self.assertEqual(m.check_managed(self.target,m.catalog(m.catalog_bytes(self.target))['plugins'][1])['version'],'1.0.0')
        p,_=m.plan(self.target,'unregister',name='sample')
        result=m.apply(self.target,'unregister',name='sample',expected=p['plan_digest'])
        self.assertEqual(m.catalog(m.catalog_bytes(self.target))['plugins'],[{'name':'unrelated','source':'./elsewhere'}])
        m.recover(self.target,result['transaction'])
        self.assertEqual(len(m.catalog(m.catalog_bytes(self.target))['plugins']),2)
        self.assertTrue(list((self.target/'plugins'/'sample'/'2.0.0').iterdir()))

    def test_N5_hash_schema_version_and_path(self):
        (self.source/'skills/hello/SKILL.md').write_text('changed')
        with self.assertRaisesRegex(m.ManagerError,'hash'): m.validate(self.source)
        self.seal(self.source)
        data=json.loads((self.source/'manager.json').read_bytes()); data['schema_version']=2
        (self.source/'manager.json').write_bytes(m.encoded(data))
        with self.assertRaisesRegex(m.ManagerError,'schema'): m.validate(self.source)
        for name in ['../escape','C:/escape','x\\y','/escape','CON.txt','a/../b','a.']:
            with self.subTest(path=name), self.assertRaises(m.ManagerError): m.within(self.target,name)

    def test_N5_links(self):
        try: (self.source/'link').symlink_to(self.source/'plugin.json')
        except OSError: self.skipTest('OS does not permit creating symlinks')
        with self.assertRaises(m.ManagerError): m.validate(self.source)

    def test_N5_link_guard_simulated(self):
        with mock.patch.object(Path,'is_symlink',return_value=True):
            with self.assertRaisesRegex(m.ManagerError,'links'): m.safe_tree_path(self.source)

    def test_N6_permission_denial_stops_before_commit(self):
        p,_=m.plan(self.target,'register',self.source)
        with mock.patch.object(m,'atomic',side_effect=PermissionError('simulated denied write')):
            with self.assertRaises(PermissionError): m.apply(self.target,'register',self.source,expected=p['plan_digest'])
        self.assertIsNone(m.catalog_bytes(self.target))
        self.assertFalse((self.target/m.STATE/'writer.lock').exists())

    def test_N5_duplicate_json_and_unknown_manifest_fields(self):
        with self.assertRaisesRegex(m.ManagerError,'Duplicate'): m.read_json('{"name":1,"name":2}')
        data=json.loads((self.source/'plugin.json').read_bytes()); data['hooks']={}
        (self.source/'plugin.json').write_bytes(m.encoded(data)); self.seal(self.source)
        with self.assertRaisesRegex(m.ManagerError,'Unsupported plugin fields'): m.validate(self.source)

    def test_N5_size_and_invalid_version(self):
        (self.source/'large.bin').write_bytes(b'x'*(m.MAX_BYTES+1))
        with self.assertRaisesRegex(m.ManagerError,'size'): m.validate(self.source)
        (self.source/'large.bin').unlink()
        data=json.loads((self.source/'plugin.json').read_bytes()); data['version']='../bad'
        (self.source/'plugin.json').write_bytes(m.encoded(data)); self.seal(self.source)
        with self.assertRaisesRegex(m.ManagerError,'version'): m.validate(self.source)

    def test_N6_dirty_source_and_stale_plan(self):
        p,_=m.plan(self.target,'register',self.source)
        m.atomic(m.within(self.target,m.CATALOG),m.encoded({'name':'other','plugins':[]}))
        with self.assertRaisesRegex(m.ManagerError,'Plan changed'): m.apply(self.target,'register',self.source,expected=p['plan_digest'])
        self.install()
        entry=m.catalog(m.catalog_bytes(self.target))['plugins'][0]
        location=m.within(self.target,entry['source']['path'][2:])
        (location/'skills/hello/SKILL.md').write_text('user edit')
        with self.assertRaises(m.ManagerError): m.plan(self.target,'unregister',name='sample')

    def test_N6_rollback_catalog_drift(self):
        tx=self.install()['transaction']
        m.atomic(m.within(self.target,m.CATALOG),m.encoded({'name':'edited','plugins':[]}))
        with self.assertRaisesRegex(m.ManagerError,'drift'): m.recover(self.target,tx)

    def test_N6_same_version_replacement(self):
        self.install()
        (self.source/'extra.md').write_text('new content'); self.seal(self.source)
        with self.assertRaisesRegex(m.ManagerError,'Same-version'): m.plan(self.target,'register',self.source)

    def test_N7_interruptions_and_recovery(self):
        for fault in ['before-commit','after-commit']:
            with self.subTest(fault=fault):
                with self.assertRaisesRegex(m.ManagerError,'Injected'): self.install(fault=fault)
                with self.assertRaisesRegex(m.ManagerError,'Pending'): m.plan(self.target,'register',self.source)
                m.recover(self.target)
                self.assertIsNone(m.catalog_bytes(self.target))
        self.install()

    def test_N7_lock(self):
        with m.Lock(self.target):
            with self.assertRaisesRegex(m.ManagerError,'lock'): self.install()

    def test_reverse_dependencies(self):
        self.install()
        child=self.make_package('child',dependencies={'sample':'1.0.0'})
        self.install(child)
        with self.assertRaisesRegex(m.ManagerError,'required'): m.plan(self.target,'unregister',name='sample')
        upgrade=self.make_package('sample','2.0.0')
        with self.assertRaisesRegex(m.ManagerError,'break dependent'): m.plan(self.target,'register',upgrade)

    def test_reject_active_integrations_and_missing_code_permission(self):
        (self.source/'mcp.json').write_text('{}'); self.seal(self.source)
        with self.assertRaisesRegex(m.ManagerError,'unsupported'): m.validate(self.source)
        (self.source/'mcp.json').unlink()
        (self.source/'code.py').write_text('raise RuntimeError("must never execute")'); self.seal(self.source)
        with self.assertRaisesRegex(m.ManagerError,'local-code'): m.validate(self.source)
        self.seal(self.source,['local-code'])
        self.install(grants=['local-code'])

    def test_unmanaged_catalog_entry_preserved(self):
        m.atomic(m.within(self.target,m.CATALOG),m.encoded({'name':'existing','plugins':[{'name':'sample','source':'./custom'}]}))
        with self.assertRaisesRegex(m.ManagerError,'not managed'): self.install()

if __name__ == '__main__': unittest.main()
