import ctypes
from dataclasses import dataclass
from typing import Dict, List, Optional

try:
    winmmdll = ctypes.WinDLL('winmm.dll')

    # [joyGetNumDevs](https://docs.microsoft.com/en-us/windows/win32/api/joystickapi/nf-joystickapi-joygetnumdevs)
    """
    UINT joyGetNumDevs();
    """
    _joyGetNumDevs_proto = ctypes.WINFUNCTYPE(ctypes.c_uint)
    _joyGetNumDevs_func = _joyGetNumDevs_proto(("joyGetNumDevs", winmmdll))

    # [joyGetDevCaps](https://docs.microsoft.com/en-us/windows/win32/api/joystickapi/nf-joystickapi-joygetdevcaps)
    """
    MMRESULT joyGetDevCaps(UINT uJoyID, LPJOYCAPS pjc, UINT cbjc);

    32 bit: joyGetDevCapsA
    64 bit: joyGetDevCapsW

    sizeof(JOYCAPS): 728
    """
    _joyGetDevCaps_proto = ctypes.WINFUNCTYPE(ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint)
    _joyGetDevCaps_param = (1, "uJoyID", 0), (1, "pjc", None), (1, "cbjc", 0)
    _joyGetDevCaps_func = _joyGetDevCaps_proto(("joyGetDevCapsW", winmmdll), _joyGetDevCaps_param)

    # [joyGetPosEx](https://docs.microsoft.com/en-us/windows/win32/api/joystickapi/nf-joystickapi-joygetposex)
    """
    MMRESULT joyGetPosEx(UINT uJoyID, LPJOYINFOEX pji);
    sizeof(JOYINFOEX): 52
    """
    _joyGetPosEx_proto = ctypes.WINFUNCTYPE(ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p)
    _joyGetPosEx_param = (1, "uJoyID", 0), (1, "pji", None)
    _joyGetPosEx_func = _joyGetPosEx_proto(("joyGetPosEx", winmmdll), _joyGetPosEx_param)
except:
    winmmdll = None

JOYERR_NOERROR = 0
JOY_RETURNX = 0x00000001
JOY_RETURNY = 0x00000002
JOY_RETURNZ = 0x00000004
JOY_RETURNR = 0x00000008
JOY_RETURNU = 0x00000010
JOY_RETURNV = 0x00000020
JOY_RETURNPOV = 0x00000040
JOY_RETURNBUTTONS = 0x00000080
JOY_RETURNRAWDATA = 0x00000100
JOY_RETURNPOVCTS = 0x00000200
JOY_RETURNCENTERED = 0x00000400
JOY_USEDEADZONE = 0x00000800
JOY_RETURNALL = (JOY_RETURNX | JOY_RETURNY | JOY_RETURNZ |
                 JOY_RETURNR | JOY_RETURNU | JOY_RETURNV |
                 JOY_RETURNPOV | JOY_RETURNBUTTONS)

_CAPS_SIZE_W = 728
_CAPS_OFFSET_V = 4 + 32 * 2


# joystickapi - joyGetNumDevs
def _joyGetNumDevs():
    try:
        num = _joyGetNumDevs_func()
    except:
        num = 0
    return num


def _joyGetDevCaps(uJoyID):
    try:
        buffer = (ctypes.c_ubyte * _CAPS_SIZE_W)()
        p1 = ctypes.c_uint(uJoyID)
        p2 = ctypes.cast(buffer, ctypes.c_void_p)
        p3 = ctypes.c_uint(_CAPS_SIZE_W)
        ret_val = _joyGetDevCaps_func(p1, p2, p3)
        ret = None if ret_val != JOYERR_NOERROR else buffer
    except:
        ret = None
    return ret


def _joyGetPosEx(uJoyID):
    try:
        buffer = (ctypes.c_uint32 * (_JOYINFO_SIZE // 4))()
        buffer[0] = _JOYINFO_SIZE
        buffer[1] = JOY_RETURNALL
        p1 = ctypes.c_uint(uJoyID)
        p2 = ctypes.cast(buffer, ctypes.c_void_p)
        ret_val = _joyGetPosEx_func(p1, p2)
        ret = None if ret_val != JOYERR_NOERROR else buffer
    except:
        ret = None
    return ret


@dataclass
class ChannelCaps:
    min: int
    max: int


@dataclass
class Joystick:
    id: int
    axes: Dict[str, ChannelCaps]
    buttons: int

    def __init__(self, uJoyID):
        self.id = uJoyID
        self.loaded = False

    def _load(self, buffer):
        ushort_array = (ctypes.c_uint16 * 2).from_buffer(buffer)
        self.wMid, self.wPid = ushort_array

        wchar_array = (ctypes.c_wchar * 32).from_buffer(buffer, 4)
        self.szPname = ctypes.cast(wchar_array, ctypes.c_wchar_p).value

        uint_array = (ctypes.c_uint32 * 19).from_buffer(buffer, _CAPS_OFFSET_V)
        self.wXmin, self.wXmax, self.wYmin, self.wYmax, self.wZmin, self.wZmax, \
            self.wNumButtons, self.wPeriodMin, self.wPeriodMax, \
            self.wRmin, self.wRmax, self.wUmin, self.wUmax, self.wVmin, self.wVmax, \
            self.wCaps, self.wMaxAxes, self.wNumAxes, self.wMaxButtons = uint_array

        self.axes = {
            "X": ChannelCaps(self.wXmin, self.wXmax),
            "Y": ChannelCaps(self.wYmin, self.wYmax),
            "Z": ChannelCaps(self.wZmin, self.wZmax),
            "RX": ChannelCaps(self.wRmin, self.wRmax),
            "RY": ChannelCaps(self.wUmin, self.wUmax),
            "RZ": ChannelCaps(self.wVmin, self.wVmax),
        }
        self.buttons = self.wNumButtons

    def get(self) -> Optional["JoyValues"]:
        if not self.loaded:
            self._load(_joyGetDevCaps(self.id))
        buf = _joyGetPosEx(self.id)
        if buf is None:
            return None
        return JoyValues(buf, self.buttons)


_JOYINFO_SIZE = 52


@dataclass
class JoyValues:
    axes: Dict[str, int]
    buttons: List[int]

    def __init__(self, buffer, n_buttons):
        uint_array = (ctypes.c_uint32 * (_JOYINFO_SIZE // 4)).from_buffer(buffer)
        self.dwSize, self.dwFlags, \
            self.dwXpos, self.dwYpos, self.dwZpos, self.dwRpos, self.dwUpos, self.dwVpos, \
            self.dwButtons, self.dwButtonNumber, self.dwPOV, self.dwReserved1, self.dwReserved2 = uint_array

        self.axes = {
            "X": self.dwXpos,
            "Y": self.dwYpos,
            "Z": self.dwZpos,
            "RX": self.dwRpos,
            "RY": self.dwUpos,
            "RZ": self.dwVpos,
        }
        self.buttons = [self.dwButtons & 2 ** b != 0 for b in range(n_buttons)]


def get_joysticks() -> List[Joystick]:
    ret = []
    for i in range(_joyGetNumDevs()):
        caps_buf = _joyGetDevCaps(i)
        if caps_buf is not None:
            joy = Joystick(i)
            # noinspection PyProtectedMember
            joy._load(caps_buf)
            ret.append(joy)
    return ret


if __name__ == '__main__':
    import sys
    import time

    joysticks = get_joysticks()
    if len(joysticks) == 0:
        print("No joysticks")
        sys.exit(1)
    joystick = joysticks[0]
    print(joystick)

    while True:
        print(joystick.get())
        time.sleep(0.1)
