from enum import Enum


class Classification(Enum):
    RT_NO_IUF = "RT_NO_IUF"
    RT_NO_IUD = "RT_NO_IUD"
    IUV_NO_RT = "IUV_NO_RT"
    TES_NO_IUF_OR_IUV = "TES_NO_IUF_OR_IUV"
    IUF_NO_TES = "IUF_NO_TES"
    IUD_RT_IUF = "IUD_RT_IUF"
    RT_IUF = "RT_IUF"
    RT_TES = "RT_TES"
    IUD_RT_IUF_TES = "IUD_RT_IUF_TES"
    RT_IUF_TES = "RT_IUF_TES"
    IUF_TES_DIV_IMP = "IUF_TES_DIV_IMP"
    IUD_NO_RT = "IUD_NO_RT"
    TES_NO_MATCH = "TES_NO_MATCH"
