# GOLIATH_ALIGN_* env + Python sys.path.
# MOJO_ALIGN_* and METHYLGRAPHER_MOJO_* are one-cycle fallbacks.

from std.collections import List
from std.python import Python, PythonObject


def _env_nonempty(os_mod: PythonObject, key: String) raises -> String:
    var raw = String(os_mod.environ.get(key, ""))
    return String(raw.strip())


def getenv_align(suffix: String, default: String = "") raises -> String:
    var os_mod = Python.import_module("os")
    var canon_key = "GOLIATH_ALIGN_" + suffix
    var mid_key = "MOJO_ALIGN_" + suffix
    var old_key = "METHYLGRAPHER_MOJO_" + suffix
    var value = _env_nonempty(os_mod, canon_key)
    if value.byte_length() > 0:
        return value
    var mid = _env_nonempty(os_mod, mid_key)
    if mid.byte_length() > 0:
        print("warning: ", mid_key, " is deprecated; use ", canon_key, flush=True)
        return mid
    var legacy = _env_nonempty(os_mod, old_key)
    if legacy.byte_length() > 0:
        print("warning: ", old_key, " is deprecated; use ", canon_key, flush=True)
        return legacy
    return default


def install_prefix() raises -> String:
    var os_mod = Python.import_module("os")
    if Bool(os_mod.path.isdir("/opt/goliath-align")):
        return "/opt/goliath-align"
    if Bool(os_mod.path.isdir("/opt/mojo-align")):
        print(
            "warning: /opt/mojo-align is deprecated; use /opt/goliath-align",
            flush=True,
        )
        return "/opt/mojo-align"
    if Bool(os_mod.path.isdir("/opt/methylgrapher-mojo")):
        print(
            "warning: /opt/methylgrapher-mojo is deprecated; use /opt/goliath-align",
            flush=True,
        )
        return "/opt/methylgrapher-mojo"
    return "/opt/goliath-align"


def _insert_path(sys_mod: PythonObject, path: String) raises:
    if path.byte_length() == 0:
        return
    sys_mod.path.insert(0, path)


def ensure_python_path() raises:
    """cwd, GOLIATH_ALIGN_ROOT, /opt/goliath-align — never a developer home path."""
    var os_mod = Python.import_module("os")
    var sys_mod = Python.import_module("sys")
    var cwd = String(os_mod.getcwd())
    var root = getenv_align("ROOT", "")
    var prefix = install_prefix()
    _insert_path(sys_mod, prefix + "/gpu-common/python")
    _insert_path(sys_mod, prefix + "/fq2bam-meth/python")
    _insert_path(sys_mod, prefix + "/giraffe/python")
    _insert_path(sys_mod, prefix + "/scripts")
    _insert_path(sys_mod, prefix + "/methylgrapher")
    _insert_path(sys_mod, prefix)
    if root.byte_length() > 0:
        _insert_path(sys_mod, root + "/gpu-common/python")
        _insert_path(sys_mod, root + "/fq2bam-meth/python")
        _insert_path(sys_mod, root + "/giraffe/python")
        _insert_path(sys_mod, root + "/scripts")
        _insert_path(sys_mod, root + "/methylgrapher")
        _insert_path(sys_mod, root)
    _insert_path(sys_mod, cwd + "/gpu-common/python")
    _insert_path(sys_mod, cwd + "/fq2bam-meth/python")
    _insert_path(sys_mod, cwd + "/giraffe/python")
    _insert_path(sys_mod, cwd + "/giraffe/scripts")
    _insert_path(sys_mod, cwd + "/methylgrapher")
    _insert_path(sys_mod, cwd)


def giraffe_fixture_root() raises -> String:
    """In-repo (or staged) giraffe test fixture directory."""
    var os_mod = Python.import_module("os")
    var cwd = String(os_mod.getcwd())
    var root = getenv_align("ROOT", "")
    var cands = List[String]()
    cands.append(cwd + "/giraffe/tests/data/giraffe_fixture")
    cands.append(cwd + "/tests/data/giraffe_fixture")
    if root.byte_length() > 0:
        cands.append(root + "/giraffe/tests/data/giraffe_fixture")
        cands.append(root + "/tests/data/giraffe_fixture")
    for p in cands:
        if Bool(os_mod.path.isdir(p)):
            return p
    raise Error("giraffe_fixture not found under cwd or GOLIATH_ALIGN_ROOT")
