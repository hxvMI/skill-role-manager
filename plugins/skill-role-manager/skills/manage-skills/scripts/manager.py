"""Offline, explicit-plan local marketplace manager. Never runs package code."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import uuid

ID = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")
VERSION = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-[a-z0-9.-]+)?\Z")
MAX_BYTES = 16 * 1024 * 1024
CATALOG = '.agents/plugins/marketplace.json'
STATE = '.skill-role-manager'

class ManagerError(Exception):
    pass

def require(condition, message):
    if not condition:
        raise ManagerError(message)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode('utf-8')

def read_json(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'Duplicate JSON key')
            result[key] = value
        return result
    try:
        return json.loads(data, object_pairs_hook=unique)
    except (ValueError, UnicodeError) as exc:
        raise ManagerError('Invalid JSON') from exc

def safe_tree_path(path):
    path = Path(path).absolute()
    for node in [path, *path.parents]:
        require(not node.is_symlink(), 'Symbolic links are not supported')
        if node.exists():
            require(not (getattr(node.lstat(),'st_file_attributes',0) & getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',0)), 'Reparse paths are not supported')
        if hasattr(node, 'is_junction'):
            require(not node.is_junction(), 'Junctions are not supported')
    return path.resolve()

def within(root, relative):
    require(isinstance(relative, str) and relative, 'Empty path')
    parts = PurePosixPath(relative).parts
    require(not relative.startswith('/') and '\\' not in relative and ':' not in relative,
            'Only portable relative paths are supported')
    require(all(part not in ('', '.', '..') for part in relative.split('/')), 'Unsafe path')
    require(all(not part.endswith(('.', ' ')) for part in parts), 'Unsafe Windows path')
    reserved = {'con', 'prn', 'aux', 'nul', *('com'+str(i) for i in range(1,10)), *('lpt'+str(i) for i in range(1,10))}
    require(all(part.split('.')[0].lower() not in reserved for part in parts), 'Reserved path')
    result = safe_tree_path(root.joinpath(*parts))
    require(result.is_relative_to(root), 'Path escapes root')
    return result

def tree(root):
    result = {}
    total = 0
    for item in sorted(root.rglob('*')):
        safe_tree_path(item)
        if item.is_dir():
            continue
        require(item.is_file(), 'Only regular files supported')
        require(len(result) < 2048, 'Too many files')
        relative = item.relative_to(root).as_posix()
        within(root, relative)
        total += item.stat().st_size
        require(total <= MAX_BYTES, 'Package size limit exceeded')
        result[relative] = item.read_bytes()
    require(len({name.casefold() for name in result}) == len(result), 'Case-colliding files')
    return result

def validate(source):
    source = safe_tree_path(source)
    require(source.is_dir(), 'Source must be an extracted local directory')
    files = tree(source)
    require('plugin.json' in files and 'manager.json' in files, 'plugin.json and manager.json required')
    plugin, contract = read_json(files['plugin.json']), read_json(files['manager.json'])
    require(isinstance(plugin, dict) and isinstance(contract, dict), 'Manifest must be an object')
    require(set(plugin) <= {'$schema','name','version','description','license','author','homepage','repository','keywords'}, 'Unsupported plugin fields')
    name, version = plugin.get('name'), plugin.get('version')
    require(isinstance(name, str) and ID.fullmatch(name) and len(name) <= 64, 'Invalid plugin ID')
    require(isinstance(version, str) and VERSION.fullmatch(version), 'Invalid semantic version')
    require(plugin.get('$schema') == 'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json', 'Unsupported plugin schema')
    require(isinstance(plugin.get('description'), str) and plugin['description'], 'Description required')
    require(contract.get('schema_version') == 1 and type(contract.get('schema_version')) is int, 'Unsupported manager schema')
    require(set(contract) == {'schema_version', 'id', 'version', 'permissions', 'dependencies', 'files'}, 'Unknown/missing manager fields')
    require(contract['id'] == name and contract['version'] == version, 'Identity mismatch')
    permissions = contract['permissions']
    require(isinstance(permissions, list) and all(isinstance(x,str) and ID.fullmatch(x) for x in permissions)
            and len(permissions) == len(set(permissions)), 'Invalid permissions')
    dependencies = contract['dependencies']
    require(isinstance(dependencies, dict), 'Dependencies must be exact-version object')
    require(all(ID.fullmatch(k) and isinstance(v,str) and VERSION.fullmatch(v) and k != name
                for k,v in dependencies.items()), 'Invalid dependencies')
    hashes = contract['files']
    require(isinstance(hashes, dict) and set(hashes) == set(files)-{'manager.json'}, 'File inventory mismatch')
    for relative, expected in hashes.items():
        within(source, relative)
        require(isinstance(expected, str) and digest(files[relative]) == expected, 'File hash mismatch: '+relative)
    forbidden = ('hooks/', 'mcp.json', '.mcp.json', '.app.json')
    require(not any(n.startswith(forbidden) for n in files), 'Hooks and MCP/app integrations unsupported')
    require(not plugin.get('extensions'), 'Plugin extensions unsupported in skills-only v0.1')
    if '.codex-plugin/plugin.json' in files:
        overlay = read_json(files['.codex-plugin/plugin.json'])
        require(set(overlay) <= {'name','version','description','skills'}, 'Unsupported compatibility fields')
        require(overlay.get('name') == name and overlay.get('version') == version and overlay.get('skills') == './skills/', 'Invalid compatibility overlay')
    skills = [n for n in files if re.fullmatch(r'skills/[^/]+/SKILL.md', n)]
    require(skills, 'At least one SKILL.md required')
    for skill in skills:
        text = files[skill].decode('utf-8-sig').replace('\r\n','\n')
        expected = skill.split('/')[1]
        require(ID.fullmatch(expected), 'Invalid skill ID')
        require(text.startswith('---\n') and '\n---\n' in text[4:], 'Skill frontmatter required')
        front = text.split('---', 2)[1]
        require(re.search(r'^name: '+re.escape(expected)+r'\s*$', front, re.M) and re.search(r'^description: .+', front,re.M), 'Skill metadata mismatch')
    if any(Path(n).suffix.lower() in ('.py','.sh','.ps1','.exe','.js','.bat','.cmd') for n in files):
        require('local-code' in permissions, 'Executable content requires local-code declaration')
    return {'id':name, 'version':version, 'permissions':permissions, 'dependencies':dependencies,
            'digest':digest(encoded({n:digest(b) for n,b in files.items()})), 'files':files}

def target_root(root):
    root = safe_tree_path(root)
    require(root.is_dir(), 'Create/select an owner-controlled target directory first')
    return root

def catalog_bytes(root):
    path = within(root, CATALOG)
    return path.read_bytes() if path.exists() else None

def catalog(raw):
    result = read_json(raw) if raw is not None else {'name':'skill-role-local','plugins':[]}
    require(isinstance(result,dict) and isinstance(result.get('name'),str) and isinstance(result.get('plugins'),list), 'Invalid marketplace')
    names = [entry.get('name') for entry in result['plugins'] if isinstance(entry,dict)]
    require(len(names) == len(result['plugins']) and all(isinstance(n,str) for n in names) and len(set(names)) == len(names), 'Invalid/duplicate marketplace entries')
    return result

def source_path(package):
    return f"plugins/{package['id']}/{package['version']}/{package['digest']}"

def managed_entry(package):
    return {'name':package['id'], 'source':{'source':'local','path':'./'+source_path(package)},
            'policy':{'installation':'AVAILABLE','authentication':'ON_INSTALL'}, 'category':'Productivity'}

def check_managed(root, entry):
    source = entry.get('source', {})
    require(isinstance(source,dict) and source.get('source') == 'local', 'Entry not managed by this tool')
    path = source.get('path','')
    match = re.fullmatch(r'\./plugins/([a-z0-9-]+)/([^/]+)/([a-f0-9]{64})',path)
    require(match and match[1] == entry['name'], 'Entry not managed by this tool')
    package = validate(within(root, path[2:]))
    require(package['digest'] == match[3] and package['version'] == match[2], 'Managed source was modified')
    return package

def plan(root, operation, source=None, name=None, grants=()):
    root = target_root(root)
    require(not within(root, STATE+'/pending.json').exists(), 'Pending transaction: run recover --apply')
    raw = catalog_bytes(root)
    current = catalog(raw)
    package = validate(source) if operation == 'register' else None
    name = package['id'] if package else name
    require(isinstance(name,str) and ID.fullmatch(name), 'Valid plugin ID required')
    old = next((e for e in current['plugins'] if e['name'] == name),None)
    if old:
        check_managed(root, old)
    if package:
        require(set(package['permissions']) <= set(grants), 'Missing permission grants: '+','.join(sorted(set(package['permissions'])-set(grants))))
        for dep, version in package['dependencies'].items():
            entry = next((e for e in current['plugins'] if e['name'] == dep),None)
            require(entry is not None and check_managed(root,entry)['version'] == version, 'Missing/incompatible dependency: '+dep)
        new_entry = managed_entry(package)
        for dependent in current['plugins']:
            if dependent['name'] != name and isinstance(dependent.get('source'),dict) and str(dependent['source'].get('path','')).startswith('./plugins/'):
                required_version = check_managed(root,dependent)['dependencies'].get(name)
                require(required_version is None or required_version == package['version'], 'Update would break dependent '+dependent['name'])
        if old and old != new_entry:
            require(check_managed(root,old)['version'] != package['version'], 'Same-version content replacement refused; increment version')
        after = {**current,'plugins':[e for e in current['plugins'] if e['name'] != name]+[new_entry]}
        noop = old == new_entry
    else:
        require(operation == 'unregister' and old, 'Managed registration not found')
        for entry in current['plugins']:
            if entry['name'] != name and isinstance(entry.get('source'),dict) and str(entry['source'].get('path','')).startswith('./plugins/'):
                require(name not in check_managed(root,entry)['dependencies'], 'Registration required by '+entry['name'])
        after = {**current,'plugins':[e for e in current['plugins'] if e['name'] != name]}
        noop = False
    result = {'operation':operation,'id':name,'target':str(root),'catalog_before':digest(raw or b''),
              'catalog_after':after,'source_digest':package['digest'] if package else None,
              'permissions':package['permissions'] if package else [],'dependencies':package['dependencies'] if package else {},
              'noop':noop,'effect':'registration only; native host installation/activation not verified'}
    result['plan_digest'] = digest(encoded(result))
    return result, package

def atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        with tmp.open('xb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp,path)
    finally:
        if tmp.exists():
            tmp.unlink()

class Lock:
    def __init__(self, root):
        self.path = within(root, STATE+'/writer.lock')
    def __enter__(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        try:
            with self.path.open('x') as stream:
                stream.write(str(os.getpid()))
        except FileExistsError as exc:
            raise ManagerError('Writer lock exists; verify no process is active before manual removal') from exc
    def __exit__(self,*args):
        self.path.unlink()

def apply(root, operation, source=None, name=None, grants=(), expected=None, fault=None):
    root = target_root(root)
    with Lock(root):
        intent, package = plan(root,operation,source,name,grants)
        require(expected == intent['plan_digest'], 'Plan changed or digest missing; review a fresh plan')
        if intent['noop']:
            return intent
        before = catalog_bytes(root)
        after = encoded(intent['catalog_after'])
        journal = {'schema_version':1,'transaction':uuid.uuid4().hex,
                   'before':base64.b64encode(before).decode() if before is not None else None,
                   'after':base64.b64encode(after).decode()}
        pending = within(root,STATE+'/pending.json')
        atomic(pending,encoded(journal))
        if package:
            destination = within(root,source_path(package))
            if destination.exists():
                require(validate(destination)['digest'] == package['digest'], 'Existing revision differs')
            else:
                staging = within(root,STATE+'/staging/'+journal['transaction'])
                for relative, data in package['files'].items():
                    atomic(within(staging,relative), data)
                require(validate(staging)['digest'] == package['digest'], 'Staged content mismatch')
                destination.parent.mkdir(parents=True,exist_ok=True)
                staging.rename(destination)
        if fault == 'before-commit':
            raise ManagerError('Injected interruption before commit')
        require(catalog_bytes(root) == before, 'Catalog changed during transaction')
        atomic(within(root,CATALOG), after)
        if fault == 'after-commit':
            raise ManagerError('Injected interruption after commit')
        atomic(within(root,STATE+'/history/'+journal['transaction']+'.json'),encoded(journal))
        pending.unlink()
        return {**intent,'transaction':journal['transaction']}

def restore(root, record):
    require(record.get('schema_version') == 1, 'Unknown journal schema')
    before = base64.b64decode(record['before'],validate=True) if record['before'] is not None else None
    after = base64.b64decode(record['after'],validate=True)
    require(catalog_bytes(root) in (before,after), 'Catalog drift: recovery refused')
    if before is None:
        path = within(root,CATALOG)
        if path.exists():
            path.unlink()
    else:
        atomic(within(root,CATALOG),before)

def recover(root, transaction=None):
    root = target_root(root)
    with Lock(root):
        pending = within(root,STATE+'/pending.json')
        if transaction is not None:
            require(not pending.exists(), 'Recover pending transaction first')
            require(re.fullmatch('[a-f0-9]{32}',transaction), 'Invalid transaction ID')
            record_path = within(root,STATE+'/history/'+transaction+'.json')
        else:
            require(pending.exists(), 'No pending transaction')
            record_path = pending
        record = read_json(record_path.read_bytes())
        restore(root,record)
        if transaction is None:
            atomic(within(root,STATE+'/history/'+record['transaction']+'.json'),encoded(record))
            pending.unlink()
        return {'restored':record['transaction'],'native_host_cache':'unchanged','source_revisions':'retained'}

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['validate','plan','register','list','unregister','rollback','recover'])
    parser.add_argument('--source')
    parser.add_argument('--target')
    parser.add_argument('--id')
    parser.add_argument('--grant',action='append',default=[])
    parser.add_argument('--apply',action='store_true',help='Required for any mutation')
    parser.add_argument('--plan-digest')
    parser.add_argument('--transaction')
    args = parser.parse_args(argv)
    try:
        if args.command == 'validate':
            require(args.source,'--source required')
            result = {k:v for k,v in validate(args.source).items() if k != 'files'}
        else:
            require(args.target,'--target required')
            root = target_root(args.target)
            if args.command == 'list':
                result = {'catalog':catalog(catalog_bytes(root)),'activation':'not verified'}
            elif args.command in ('recover','rollback'):
                require(args.apply,'Review recovery scope; --apply required')
                require(args.command != 'rollback' or args.transaction,'--transaction required')
                result = recover(root,args.transaction if args.command == 'rollback' else None)
            else:
                operation = 'unregister' if args.command == 'unregister' else 'register'
                require(operation != 'register' or args.source,'--source required')
                if args.apply:
                    require(args.command != 'plan','plan is read-only')
                    result = apply(root,operation,args.source,args.id,args.grant,args.plan_digest)
                else:
                    result,_ = plan(root,operation,args.source,args.id,args.grant)
        print(json.dumps(result,indent=2))
        return 0
    except (ManagerError,OSError,ValueError,KeyError,TypeError) as exc:
        print(json.dumps({'error':str(exc),'status':'stopped'}),file=sys.stderr)
        return 2

if __name__ == '__main__':
    sys.exit(main())
