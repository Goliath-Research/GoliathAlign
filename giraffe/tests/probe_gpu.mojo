from max.gpu.host import DeviceContext
from std.sys import has_accelerator

def main() raises:
    print("has_accelerator=", has_accelerator())
    if has_accelerator():
        var ctx = DeviceContext()
        print("device ok")
    else:
        print("no accelerator")
