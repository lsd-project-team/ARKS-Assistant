from app.api.knowledge import SnapshotFile, check_files


def test_snapshot_check_detects_changes_and_missing_files(services):
    workspace = services[2]
    version = workspace.read('Program.cs')['version']
    files = [
        SnapshotFile(id='same', path='Program.cs', sha256=version),
        SnapshotFile(id='changed', path='Program.cs', sha256='0' * 64),
        SnapshotFile(id='missing', path='Missing.cs', sha256=version),
    ]
    result = check_files(workspace, files)
    assert result['same'] == {'status': 'match', 'version': version}
    assert result['changed']['status'] == 'changed'
    assert result['missing']['status'] == 'missing'


def test_snapshot_check_keeps_workspace_boundary(services):
    workspace = services[2]
    files = [SnapshotFile(id=str(i), path=path) for i, path in enumerate([
        '../data/app.sqlite3', 'C:/Windows/win.ini', '/Windows/win.ini', '.git/config',
    ])]
    assert all(row['status'] == 'unavailable' for row in check_files(workspace, files).values())


def test_snapshot_check_hashes_original_encoded_bytes(services):
    workspace = services[2]
    target = workspace.root / 'Encoded.cs'
    target.write_bytes('class 中文 {}\r\n'.encode('utf-16'))
    version = workspace.read('Encoded.cs')['version']
    snapshot = SnapshotFile(id='utf16', path='Encoded.cs', sha256=version)
    assert check_files(workspace, [snapshot])['utf16']['status'] == 'match'
