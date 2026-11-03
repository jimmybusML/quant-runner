"""Store only QuantAsiaDesk credentials in the user's macOS login Keychain.

No credential values in argv, logs, repository files, or return values.
"""
from __future__ import annotations
import ctypes as c
import ctypes.util
import os

S = c.CDLL("/System/Library/Frameworks/Security.framework/Security")
CF = c.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
Ptr = c.c_void_p
U32 = c.c_uint32

S.SecKeychainAddGenericPassword.argtypes = [Ptr, U32, Ptr, U32, Ptr, U32, Ptr, c.POINTER(Ptr)]
S.SecKeychainAddGenericPassword.restype = c.c_int32
S.SecKeychainFindGenericPassword.argtypes = [Ptr, U32, Ptr, U32, Ptr, c.POINTER(U32), c.POINTER(Ptr), c.POINTER(Ptr)]
S.SecKeychainFindGenericPassword.restype = c.c_int32
S.SecKeychainItemModifyAttributesAndData.argtypes = [Ptr, Ptr, U32, Ptr]
S.SecKeychainItemModifyAttributesAndData.restype = c.c_int32
S.SecKeychainItemFreeContent.argtypes = [Ptr, Ptr]
S.SecKeychainItemFreeContent.restype = c.c_int32
CF.CFRelease.argtypes = [Ptr]
CF.CFRelease.restype = None

ERR_NOT_FOUND=-25300


class KeychainError(RuntimeError):
    pass


def _bytes(service: str, account: str):
    if not isinstance(service, str) or not isinstance(account, str):
        raise ValueError("账号名称错误")
    return service.encode("utf-8"), account.encode("utf-8")


def _buffer(data: bytes):
    return c.create_string_buffer(data)


def _find(service, account, with_secret=False):
    sb,ab=_bytes(service,account)
    sbuf=_buffer(sb); abuf=_buffer(ab)
    length=U32(); password=Ptr(); item=Ptr()
    status=S.SecKeychainFindGenericPassword(
        None,len(sb),sbuf,len(ab),abuf,
        c.byref(length) if with_secret else None,
        c.byref(password) if with_secret else None,
        c.byref(item))
    return status,length,password,item


def exists(service: str, account: str):
    status,_,_,item=_find(service,account)
    if item:CF.CFRelease(item)
    return status==0


def get(service: str, account: str):
    status,length,pwd,item=_find(service,account,True)
    try:
        if status==ERR_NOT_FOUND:
            return None
        if status!=0:
            raise KeychainError("Mac 钥匙串无法读取这项连接")
        return c.string_at(pwd,length.value).decode("utf-8") if pwd else ""
    finally:
        if pwd:
            S.SecKeychainItemFreeContent(None,pwd)
        if item:
            CF.CFRelease(item)


def put(service: str, account: str, value: str):
    if not isinstance(value,str) or not value.strip():
        raise ValueError("凭证不能为空")
    sb,ab=_bytes(service,account)
    pw=value.strip().encode("utf-8")
    sbuf=_buffer(sb); abuf=_buffer(ab);pwbuf=_buffer(pw)
    status,_,_,item=_find(service,account)
    try:
        if status==ERR_NOT_FOUND:
            result=S.SecKeychainAddGenericPassword(None,len(sb),sbuf,len(ab),abuf,len(pw),pwbuf,None)
        elif status==0:
            result=S.SecKeychainItemModifyAttributesAndData(item,None,len(pw),pwbuf)
        else:
            raise KeychainError("Mac 钥匙串无法连接，可能需要先解锁")
        if result!=0:
            raise KeychainError("Mac 钥匙串无法保存，错误代码 "+str(result))
    finally:
        if item:
            CF.CFRelease(item)
    return True


def delete(service: str, account: str):
    """Used only by isolated self-tests; not exposed as a dashboard action."""
    sb,ab=_bytes(service,account)
    _,_,_,item=_find(service,account)
    if not item:
        return
    try:
        fn=S.SecKeychainItemDelete
        fn.argtypes=[Ptr];fn.restype=c.c_int32
        result=fn(item)
        if result!=0:
            raise KeychainError("临时钥匙串测试记录未能清理")
    finally:
        CF.CFRelease(item)
