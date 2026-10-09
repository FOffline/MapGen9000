#!/usr/bin/env python3
"""MapGen9000 - simple FOnline map (.fomap) generator. Heavily inspired by legendary Desert Tiles Helper (dgen) by Realism.

GUI:  python MapGen9000.py
CLI:  python MapGen9000.py --cli out.fomap [--size 200 --seed 2967 ...]
Needs: numpy (single file, nothing else).

Object prototypes:
    corn       = 2369, 2370, 2371
    dry trees  = 2316, 2317, 2318, 2319, 2320, 2321
    trees      = 2066, 2943, 2944, 2945, 2946, 2947
    rocks      = 2090, 2091, 2092, 2093
    cactuses   = 2064, 2065
    grass      = 2102, 2103, 2104, 2105, 2127
    misc       = 2101, 2106-2110, 2116-2118, 2121-2124, 2082-2086, 2063, 2434, 2431
    barrels    = 2005, 2006, 2001, 2396-2399, 2551, 2552
"""
import argparse
import base64
import json

import numpy as np

DEFAULTS = dict(
    size=200, seed=2967, octaves=3, persistence=0.30, density=0.6,
    # object densities (GUI shows percentages)
    corn=0.04, dry_trees=0.03, trees=0.12, rocks=0.025, cactuses=0.025,
    grass=0.14, misc=0.02, barrels=0.01,
    grass_min=0.0, grass_max=0.75, trees_min=0.4, trees_max=1.0,
    patch_grass=1.5,
    delete_outside=True,     # remove tiles/objects outside the playable map shape
    scroll_blockers=True,
    protos=dict(
        blocker=4012,
        corn=[2369, 2370, 2371],
        dry_trees=[2316, 2317, 2318, 2319, 2320, 2321],
        trees=[2066, 2943, 2944, 2945, 2946, 2947],
        rocks=[2090, 2091, 2092, 2093],
        cactuses=[2064, 2065],
        grass=[2102, 2103, 2104, 2105, 2127],
        misc=[2101, 2106, 2107, 2108, 2109, 2110, 2116, 2117, 2118, 2121, 2122, 2123, 2124,
              2082, 2083, 2084, 2085, 2086, 2063, 2434, 2431],
        barrels=[2005, 2006, 2001, 2396, 2397, 2398, 2399, 2551, 2552],
    ),
)
ASPECT = 1.38

# ============================================================================
# TILES
# ============================================================================
# Names match your files EDG1000.FRM ... EDGS004.FRM (order = order of the arrays below)
TILE_NAMES = ['1000', '1001', '1002', '1003', '2000', '2001', '2002', '2003', '3000', '3001', '4000', '4001', '4002', '4003', '4004', '4005', '4006', '4007', '4008', '5000', '5001', '5002', '5003', '5004', '5005', '5006', '5007', '5008', '6000', '6001', '6002', '6003', '6004', '6005', '6006', '6007', '6008', '6009', '6010', '6011', '7000', '7001', '7002', '7003', 's000', 's001', 's002', 's003', 's004']
TILE_WEIGHTS = [77, 133, 140, 85, 137, 99, 66, 811, 617, 105, 398, 287, 244, 104, 44, 35, 40, 51, 78, 1974, 651, 774, 982, 655, 505, 415, 402, 16, 47, 104, 103, 89, 147, 87, 100, 84, 145, 114, 53, 114, 39, 49, 121, 22, 62, 38, 35, 65, 75]
TILE_DIRS = [(1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (-1, 1), (-1, -1), (1, -1)]

TILE_ADJ = [
    [0x800000009b12, 0x1057926c80013, 0x1000050003981, 0x200041d80, 0x2007f80104, 0x10c0415d00360, 0x40131580260, 0x1f57d64003ff1, 0xbc3f60013ff2, 0x804639813e4, 0x1d579400555b2, 0x94292000a5d0, 0xc57174004d80, 0x1c02100004d90, 0x40800008090, 0x800001010, 0x4020060001, 0x920050401, 0x1002101278e10, 0x7d6eff8026e, 0x686c7f8020e, 0xef7e7d8026c, 0x10286e7f8000e, 0x2682c7f8020e, 0x8206c7f8010e, 0x80b7f80224, 0x690c958002c, 0x210100000, 0x83680004, 0x20a05e81366, 0x1150983b80, 0x6404419e0, 0xb423f80202, 0x100067d82, 0x800f40205fe2, 0x1009106390081, 0x243125f80102, 0x201880fb0083, 0x40a100642180, 0xb17242080d92, 0x144001680102, 0x1000800003d80, 0x20850ff80129, 0x1980, 0x34a214000580, 0x502001580400, 0x1100501004080, 0x201d80140, 0x810080f80103],
    [0x2e10880006, 0x40427fc0060, 0x2a4cdc802a8, 0x128680d81106, 0x511310011d8, 0x80000029d8d, 0x41d93, 0x70fa00043d93, 0x61f600003d93, 0x80400053c80, 0x16b100025d93, 0x547d20001590, 0x506b40040d83, 0x1000014d83, 0x20182, 0x70000, 0x20000000a000, 0x40300000c010, 0x1003000042882, 0x10e05fff8027c, 0x1822d77e80060, 0x10002f7dc0164, 0x625e7f80264, 0x10403e77c03ec, 0x10e8dd6f80210, 0x4c7f80240, 0x1000023d80278, 0x11200000, 0x802010080190, 0x3365704405a4, 0x1c97a006198f, 0xa064048058e, 0x4f861c815d2, 0x44c01b00786, 0x12a3e0903d04, 0x1a47102283411, 0x14290ff80018, 0x4d046ec1613, 0x102802f81008, 0x887f80008, 0x140401780090, 0x1048240000984, 0x1a181055a1084, 0x3484, 0x1258205d80000, 0x802005880080, 0x2020082120, 0x10109000801b8, 0x841100080090],
    [0x1042800030086, 0x101b721d80503, 0x37f80210, 0x40005f80000, 0x800004ed83, 0x404a62807e0, 0x8004a0280be0, 0x5aeec0007f8c, 0x19fd6e1003fbd, 0x562bc03e1, 0x328600063d88, 0xa86c004318d, 0xa06e000878d, 0x24240000984, 0x400600003400, 0x44801, 0x2800060500, 0x2200050000, 0x4280070408, 0x1a5b977f80252, 0x1a4394ff80270, 0x1057d33dc0010, 0x1a571b7f80072, 0x1843163f80232, 0xe51137fc0270, 0x48913f80212, 0x141823f810b2, 0x40004080000, 0x10004a001064, 0x11026b1bc2, 0x84c5f81784, 0x1002017f80000, 0x445e40263dc2, 0x9084a9f80108, 0x4405817803a0, 0x2242002cd82, 0xb944281582, 0x30d100243d92, 0x18000291482, 0x144906f80000, 0x1008000081482, 0x25f80000, 0x111004b85de2, 0x200320, 0x718000000d80, 0x14b000800180, 0x204000003480, 0x1008401003d81, 0x4208004424a6],
    [0x28400035e0, 0x23c00475c9, 0xe06e0e80029, 0x80d0c4880034, 0x18139150a0dd0, 0xc00024f80006, 0x106f80012, 0x1af03f0847ff4, 0xc207f0a07df8, 0x2207c80004, 0x82fa0003fe0, 0x204400437e0, 0xc6d40000ff8, 0x480c00050380, 0x22400, 0x30020, 0xa200, 0x4004000c420, 0x2060a492c2, 0x1f5f997f8000f, 0x15d607e8000a, 0x1fa0bd80002, 0x15f1a7f8000e, 0x30f70778000f, 0x35930ef80016, 0xf807f80002, 0x34b003f80006, 0x1000080004, 0x39380011, 0x400564f80812, 0x225a3f81004, 0x8443e8000c, 0x1841c61d81c10, 0x1204c0a01189, 0x102e3580b0f, 0x80d301101881, 0x1002940062d90, 0x605d30561d85, 0x2b20001980, 0x16254100058c, 0x940020000110, 0x4a158040c, 0x1133b41c80c12, 0xc1080220, 0x15460001c88, 0x140820010180, 0x21980, 0x1240810100000, 0x960805bc0000],
    [0x10400054a0482, 0x102001ffa0200, 0x440200091d8b, 0x106000003983, 0x4c12f780380, 0x840130003d90, 0x529000a8c80, 0x1f5b971d87df3, 0x947f01dc9d83, 0x6100063d91, 0x351f22a83dd3, 0x75b9400b55b2, 0xf43d24c00fd2, 0xa04164022d93, 0x410200c2000, 0x100040011, 0x402810001000, 0x1000900009016, 0x130203cc103, 0x11b8ef7f81fec, 0x8a97ebf8238c, 0x5286e3f807ee, 0x1ac96fff803ec, 0x10a8797f803ec, 0x10285e7f80ba4, 0x3e16807e4, 0x682f7c8074e, 0x4000080000, 0x2001f80440, 0x144a404cd21e4, 0x905020483da0, 0xa800803983, 0x29a7f80480, 0xa104197582, 0x14108430d1582, 0x1802101d82100, 0x108033f80580, 0x47022f82016, 0xa002e80800, 0x14d402fc10a8, 0x5480048, 0x800040021581, 0x10000c7f91084, 0x2980, 0x100485b82502, 0x908004680000, 0x1081101080114, 0x800f80a03, 0x200f8008c],
    [0x809082588058, 0x40583ec0708, 0xc0587f80210, 0x83f80024, 0x1113006024d92, 0x218435ad, 0x10206c0001986, 0x7ff6efe83d8f, 0x13cbee0fc7f9f, 0x246002e2d80, 0x51bf43c8bd8e, 0x72d4400c358f, 0x32da00872da4, 0x15a800801f88, 0x48200010100, 0x2200020400, 0x805000004805, 0x400042803, 0x602200001104, 0x1b4f7f7fc2ff0, 0x1841575fc33f2, 0x95bdb7fd13f4, 0x1953db3fc0ff0, 0x18439bffa07e0, 0x353959f887f0, 0x8401b4ec11b0, 0x1b529f2b80760, 0x480020, 0x10c1681, 0x401281898f8e, 0x3684dd318c, 0x20005f80294, 0x78004a7d80, 0x10280b37805a0, 0x8a15e278118e, 0x10031024e4d80, 0x247944f84c92, 0x53503e81c90, 0x1101788100, 0x1001107f80400, 0x140105440580, 0x800c2f80080, 0xc04dc15a2, 0x80480484, 0x41001f805a0, 0x400002181900, 0x900084001881, 0x708000a0d86, 0x9000106185],
    [0x82008004a78c, 0x902684263d8d, 0x1442027fa0000, 0x1018004f80004, 0x40200002bea0, 0x8063e80880, 0x10036e81480, 0x10e97e3f83ffd, 0x5a1ee7fc3fbc, 0x800007f81012, 0x121756283fe5, 0x8840c10837ec, 0x686c00b0fac, 0x182ae01066a8, 0x200040880, 0x60140, 0x40620000804, 0x20000002a43, 0x842004c300, 0x1f5ff7ffc4dd7, 0x194bb11fc0192, 0x1b4f113fc0412, 0x1a5f977f81193, 0x194f9b5f81582, 0x551d17f80193, 0x4f505f80412, 0x350325c83013, 0x500012, 0x1004c900a2, 0x31477c74b0, 0x60407782880, 0x140107f80000, 0x400b0392bff0, 0x1000006f80504, 0x108021f81500, 0x8005800b1dc0, 0x40a040545d80, 0x6bb0051bc8, 0xa048002318, 0x20d2a5f80890, 0x4000c0cc0, 0x5b80002, 0xa024405df5, 0x400000d80000, 0x309040281d88, 0x403c80, 0x420211884, 0x2208405031a0, 0x440c21ca0083],
    [0x14000100309a0, 0x841420120dd0, 0x18804e0251de8, 0x460002da3, 0x3083780115, 0x14020ff81028, 0x5f80001, 0x1df3ff3f83ff0, 0x1b54f67fc7ff2, 0xb5f82106, 0x9dbb35c8bfb2, 0xe039204b37d0, 0x642552342de0, 0x10001401a1fa0, 0x1001900010110, 0x4021000401, 0x60205000, 0x800900809210, 0x508527a1b22, 0xbefffff80f8f, 0x136d6c5f8010d, 0x12f687f8038e, 0x1fffcbf8058f, 0x16b0e7f835ae, 0x11e2b1f804ae, 0x22ae04e8049f, 0x4590c2b80094, 0x1800080, 0x207f80000, 0x606f801a0, 0x21405180dc0, 0x4a0666e801cf, 0x1fc07f80406, 0x600cd7c0, 0x424407a0fc6, 0x841105e03500, 0x110fd61f91d91, 0x3945eca590, 0x1100091a80, 0x1000200287d81, 0x802005602490, 0x800680001ac0, 0x913007f86186, 0x20400000184, 0x410005683d90, 0x10050c1980, 0x200020040c80, 0x400406f90001, 0x8a04d80150],
]

_ART = (
    "BAoRFQkNCwQGDgoEAwYFAwQJCBcWFBUWExISExEMCRMKCw0FBwYKDgkNCgkCBgUJCQgFCgwMCQ8LCg8QCgcLDAYMDQsODQsMDQsK"
    "DAoJCwYLCwgOBgYHCgcJCgkMBgUOCwsEBw4SBgoHBgIKCgQEBAYDBwQFFBMREhMQDw4QDgkGEAYICgMEAwcLBgkHBAQECAUFBgkP"
    "FAQMCQQDDAgEBQMGBQcDBBYVExQUEhEQERALCBIICgwEBgMJDQcLCQUGBQcEBg0GAwUSAwgTDggXEg4SEw4UDxIHBgQFBQMCBQIC"
    "BQcDBwUHCwkMBwMIBAYNDgsWCwkICQgMCgUBDAYFDwoKCgwIDAgLDg0LDA0KCgkKCQQICwMGBAgICQQKBQUFBgoJDgYECgwKDggH"
    "AgsHBg4JCwgKCwsGCRAPDQ4PDAsKDAoFCgwFCQYKCgkGDAgHBwUMCwwGBQkLDxMEDAcIBgwICAoGBwoKAwUVFBITFBIREBEQCwkS"
    "CAoLCQkICA4HCwgECwoHBAYGChEVBA4JAwMOBgMEAQMEBAQEFxYUFRYTExITEgwJFAoLDQUHBQoOCQ0KBQUGBQYHCwwICg0HAw4J"
    "AhINDA0OCw8KDQsKCQoKCQkGCQgFCgkFCQQLCgsGCwgGCAgMCxEIBgcMEhYFDwsDBA8GBAQDAgQDBgQYFxUWFxUUExQTDgsVCw0P"
    "BwgGCxAKDgwHBAcEBwkFChEVBQ0JAwMNCAIDAwMCBAYEFxYUFRUTEhETEQwJEwkLDQUHBQoOCAwKBgMFBgcHBAYNEQYJBwcDCQsF"
    "BAUHAwgEBhMSEBESDw4NDw0IBQ8GBwkCAwMGCgUJBgQEAwkEBAkKERUDDgkIBg4GBwoFBgkJAgQXFhQVFhMTEhMSDQoUCgsNCQkI"
    "Cg8JDQoFCwkHBgcHDhUZBBEMAgYRBQMHAwIGAwUDGxoYGRkXFhUXFRANFw0PEQkLCA4SDBAOBwYKAgoLCQsSFgUOCgMDDgYFBQIE"
    "BgUEBRgXFRYXFBMSFBINChQKDA4HCAYLDwoOCwYGCAQHCAYIDxMEDAcFAgsJBAUDBQUGAwQVFBITFBEQEBEQCgcSCAkLBAUDCAwH"
    "CwgDBgUHBQUEBw0RBgoHBgIKCgUEBQYEBwQGExIQERIQDw4PDgkGEAYICgMEAwYLBQkHAwUECQQEAwUMEAcJCAgECgsGBAYIAwgG"
    "BxIRDxARDg4NDg0IBA8GBggBAwQHCQQIBQUEAwoFBRILBgIXCA0YEwgcFxMXGBMZFBcCAgICAQIDBQMECQwDDAoJEA4RDAcNCQsS"
    "ExAbEA4SCwQCFwgNGBMIHBYSFhgTGRQXAgICAQIDAwQDBQkMAgwKCBAOEQsHDQkLEhMPGw8OEAkEAhQGCxYRBxoUEBQWERcSFQQD"
    "AQIDAQEDAQIHCgEKCAcODA8JBQoHCRARDRgNDBMMBgIYCQ4ZFAkdGBQYGRQaFRgBAgICAQMEBQQFCg0DDQsJERASDQgOCgwTFBEc"
    "EQ8SCwQCFgcMFxIHGxYSFhgSGBQXAwECAQICAwMCBAgMAgsKCA8OEAsGDAgKERIPGg8NDwgEAxQFChUQBxkUEBQVEBYRFAUEAgMD"
    "AQEEAQIGCQIJBwcNCw4IBAoGCA8QDRgNCxQMBgIYCQ4ZFAkdGBQYGRQaFhkBAgMCAQMEBQQFCg0DDQsJERASDQgOCgwTFBEcEQ8T"
    "DAYBGAkOGRQJHRgUGBkUGhUYAQICAgEDBAUEBQoNAw0LCREPEgwIDgoMExQRHBEPDgcDBBIDCBMOBxcSDhIUDhQQEwYFAwQFAwIE"
    "AgIFCAMHBgYLCgwHAwgFBw0OCxYLChMMBgMXCA0YEwkcFxMXGRMZFRgBBAMDAQMDBQMECQ0DDAsKEA8RDAcNCQwSExAbEA8OBwME"
    "EgQJFA8IGBIOEhQPFRATBgUDBAQCAgQCAQYIAwgGBwwKDQcDCAUHDg8LFgsKCgoFCA4FBA8KAxMODA4PChAMDwoJBwgJBwcFBwYD"
    "CAcEBwEJCQsGCQYEBQkLCxIIBgoLCAoNBwMOCQISDAwMDgsPCg0MCwkKCgkJBgkIBQoJBQkECgoLBgoIBgcIDAsRCAYQCQQCFAUK"
    "FRAIGRQQFBYQFhIVBAQCAwMCAQQCAgYKAgkIBw0MDgkFCgYJDxANGA0MBwoRFQUOCgMEDgYFBQMGBQYEBRcWFBUWFBMSExINCRQK"
    "Cw0GBwUKDwkNCgYGBwUGBwcICAwKBQILBgYPCgoKDAgMCAsODQsMDQsKCQoJBAcLAgUEBwcJBAkEBAQFCQgOBgQIAgYJDQMJDgkJ"
    "Eg0JDQ4JDwoNDAsJCgoIBwcHBgUCCAUDCAYFBwQFAwQDCAkGEQYGDAUCBhABBxEMBxUQDBASDBIOEQgHBQYHBQQFBAMDBgUFBAYJ"
    "CAoFBAYEBQsMCRQJCAYFCAwKBQYLBgcPCgcKDAYMCAsODQsMDQsKCQoJBAMLAwUFBAUGAwkCBAIHBwYOBAIHAQcKDAULDQkLEQwI"
    "DA0IDgoMDAsKCwsJCAkIBwcDCQcECgUEBgYFBQcFCggFEAcHBgEHCwsFCgwIChALBwsMBw0ICw4NCwwMCgkJCQgGAgoGBQkEAgUF"
    "BQQGBAgHBA8GBgwFBAYQAwkSDQkWEAwQEg0TDhEIBwUGBwQDBgQDBQYEBgQICggLBgQGBQUMDQkUCQgGCA8TBAwIBAMMCAUGAwYG"
    "BwIEFRQSExQSERAREAsHEggJCwUGBAgNBwsIBAcGBwQFDwgEAhQFChUQCBkUEBQVEBYRFAQEAgMDAgEFAQIGCQIJBwcNCw4JBAoG"
    "CA8QDRgNCw0QFhsGEw4JCRMFCQwHCAsLBwYdHBobGxkYFxgXEg8ZDxETDA0KEBQOEhAJDAwJCw0HCA4SCAsKBgQLCQYBBQUEBgcH"
    "FBMREhMREA8QDwoHEQcJDAMEAwcMBgoIBwIDCAYGBgMKDgkHCgoGCg4IBAgKBQsICRAPDQ4PDAsLDAoHBAwGBwoCAQMFBwQIBgcF"
    "AgwGBwcGDRELCgwJBgwKCQMHCAQHCgoTEhAREhAPDg8OCQYQCAgMAwQECAsGCgcJAwQKCAgNBgIFEQIHEw0GFxENERMNFA8SBwYE"
    "BQYDAgMDAgQHBAYFBQsJDAYEBwQGDQ4KFQoJDgYCBBIDCBMOBhcSDhITDhQQEwYFAwQFAwIDAwEEBwMHBQULCgwHBAgEBg0OCxYL"
    "CQwFBgUGCggFAw8IBgQGCwMOBAMPEAwQDw0NDgoMCwoLBwIFBAYFBAEFBAkFBgQLBAYYEggIDAMEDw4CFA8QDxcOGhAOAwQBBAMB"
    "AgIDAQIGAwYOBw0NCw0MCAgDChIOFw0HEQsCAQkFBAgICQ0JCQkRBxQKBwkLBwsKBwgJBAYFCgcGBwQHCAcGBgUDBwcLCBAHBREL"
    "BAILBwUKCAkOCwkMEQgUCggJCwcLCQcICQUIBgwICAcGCQsJBwYHBgkJCwkQCQgJCgwNBA0MAwcSBgYFAwgICwkIEhQPExIQERIN"
    "Dw4LDgoICgUDBQgIBwgMBwcICQUJCgQGBgcMCgYDEAYFBAYKAQ0CAhASDhIRDg8QCw0MCQwIAQcEBgUCAwYGCwYEAwkEBwgCCAgF"
    "DgwEAxMEBAIEBwILAQISFBAUExEREg0PDgsPCgIJAwUFBAQICA0GAgMHBAoDBxERDRcVCgscBgoJDAULCgkLGx0ZHRwZGhsWGBcU"
    "FxMLEgwMDg0NEREWDwcLAw0TAwUODgsUEggIGQMHBggECAkGCBkaFhoZFxcYFBYVEhURCA8JCgsKCg4OEwwECAIKEAYCCgoHEA4F"
    "BBQEBQQGBgQLAgQUFhIWFRITFA8REA0QDAQLBAcHBQYJCg4IAQMFBQsICQwMBg8OBAgUBQYFAwYICQgIFBYRFRQSExQPERANEAwI"
    "CwUFBggJCQoOCAcICAULCAIICAYODAQCEwUFAgQHAgsCAxIUEBQTEBESDQ8OCw4KAgkDBQUEBAgIDQYCAwcECgsEBgYECwkDAxAH"
    "AwQECgENAwIQEQ0REA4PDwsNDAkMCAIGAgQDAgQFBQoEBQIJAgcCBQ4PCxQTCAgZAgcGCAMICAYIGRsWGhkXGBkUFhUSFREJEAkK"
    "CwoLDg4TDAQIAwoQAgcQEQ0WFQoLGwQJCQoCCwcIChsdGB0bGRobFhgXFBcTCxILDA4MDRARFQ8HCgMMEgYCCgoIEA4EBRUDBQQG"
    "BgQLAgQVFhIWFRMTFBASEQ0RDQQLBQcHBgYKCg8IAQQFBgwJAwgIBQ0LBAERBgUDBQgDCwIDERMPExIPEBEMDg0KDQkBCAMFBQQD"
    "BwcMBgMECAQIBAcREQ0XFQoLGwUKCQoECwYICxsdGR0cGRobFhgXFBcTCxIMDA4MDRERFg8HCgQMEgYDCgoHEA8FBRUCBAMFBQQL"
    "AgQVFxIWFRMUFRASEQ4RDQQMBQYHBgYKCg8IAQQEBgwcFQwMDwYIEhICGBMUEhsSHhQSAgEEAQIDAwIGBAUJBQkSCxEQDxAQDAwH"
    "DhYSGxAKGhQKCg4EBhEQAhYREhEZEBwSEAECAwICAgICBQMEBwUIEAkPDw0ODgoKBQwUEBkOCBkTCQkNAwUQDwMVEBEQGQ8cEQ8C"
    "AwIDAgECAgQDAwgEBw8IDg4MDg0JCQQLExAYDggbFQsLDwUHEhECFxITEhsRHhMRAQEDAQEDAgEGBAUIBQkRChAQDhAPCwsGDRUS"
    "GhAKGRMJCQ0DBRAPAhUQERAYDxsRDwIDAQMCAQICBAMDCAQHDwgODgwODQkJBAsTDxgNBxoUCgoNBAYQEAEWERIRGRAcEhACAgID"
    "AgICAgUCAwcDBxAJDw8NDg4KCgUMFBAZDggbFQsLDwUHEhEBFxITEhsRHhMRAgIDAgEDAgIGBAUIBQkRChAQDhAPCwsGDRUSGhAK"
    "GBEKCgsEBg4OAxQPEA4XDhoQDgQFBAUEBQQEBgMFBAQFDggNDAsMCwgIAwoSDhYMBhUOBQUIAgILCwYRDA0LFAsXDQsGCAQHBgQF"
    "BgIDAgcDAwsDCgkICQkFBQQHDwsTCQQXEAkJCgQFDQwEEw4ODRYMGQ8NBAYEBQQEAwQFAgQDBQQMBwwLCQsKBwcCCBENFQsFFA0H"
    "CAcCBAoJBxALCwoTCRYMCgcJBAgHBQYHBAQDBAQBCQQJCAYIBwQEAgUOChIIAg0HAwMJCQcIBQ4JCAcJDAQQBQUNDwsPDgsMDQgK"
    "CQoJBgQGBwkHBAQGBAoIBwUMBwcOCAMCCwkHCgYNCwkICg0GEAcGDQ8KDg0LDA0ICgkMCQgFBgkLCQYFBwYKCQgHDAkIEQoKCwQG"
    "BwcHCg0ICQcQBhMJBwoMBwsKCAkKBwcGAwYDBwUGBQQGBwQGBAQLCA8FBA0GBAMJCQgIBQ4JBwcJDAQPBQUOEAsPDgwNDgkLCgsK"
    "BwQGBwkHBAQGBAoIBwULBwcNBgYHBAkIBAMOCQQFBAwDDwUDDhALDw4MDQ4JCwoHCgYDBQIDAwMDAwMIAwcECwIFCwYICAILCQID"
    "DwcFAwMLBA4FBA8RDREQDQ4PCgwLCAsHBAYBAgIEBAUFCgMFBAoBBhMMBQUGAwIJCQgPCgsJEgkVCwkICQUJCAYGBwMFBAYEAgkC"
    "CAgGBwcDAwQFDQkSBwIQCQQEBgYEBgYLDAcIBw8GEggGCwwIDAsJCQoGCAcHBwMGBAUFBAQEAgIFBQoGDwQCEQoJCgQFBgcGCg0I"
    "CAcQBhMJBwoMBwsKCAkKBwcGBAYDBgQGBQQGBgMFBAMLCA8FAxYPBgYJAgEMDAUSDQ4MFQwYDgwFBwMGBQMEBQMDAQcEBAwECwoJ"
    "CgoGBgQIEAwUCgQRCwYGBQUDCAcJDQgJCBAHEwkHCQsHCwoHCAkFBgUFBQIHAwYGBAYFAgIFBQsHEAYCDggDAgkIBggGDAoIBwkO"
    "BREHBQwOCQ4MCgsMBwkICggGBAUHCQcFAwUECQcIBg0HBhYQBwYKAQMNDAUSDQ4NFQwYDgwEBgIGBQIDBAICAQUEBAwFCwsJCgoG"
    "BgIIEAwVCgQGBQ8PCxUTCwkZCAkJCwgJDQYJGRsXGxoXGBkUFhUSFREJEAoLDAoLDw8UDQcIBgsQDQcGBgQJBwQDDQkGBQYNAxAG"
    "Aw0PCw8OCwwNCAoJBwkFAwQDBAMDAwMDCAMHBAwDBAwFBwcDCgkCAw8IBAMDCwMOBAMPEQwQDw0ODwoMCwgLBwMGAQMDAwMEBQkD"
    "BgQKAQYLBwkKAgsKAQUQBwUEBAoFDQYFEBINERAODxALDQwJDAgFBwICAgYFBQUKBAUGCQIHDAcICAIKCAMEDggDBAMLBA4GBQ4Q"
    "DBAPDA0OCQsKBwoGBQUDAgEEBQQECQUGBAsDBQwJDAwCCgkEBw8IBgUECwgOCAgPEAwQDw0NDgoMCwcLBwgHBAIECAgGBwkEBwgL"
    "BAcECAQGDQgKCQYLBwUECQcJBgQDEhIQExIPFBMOEw4KChAHBwgMBgcGDAYPDQcGBw0OCgUHCQYJDAsKDAwKBgoOCwgHBQsLCQwL"
    "CAwMBwwHCgsJCggCBQUBAQUICBAIAwYGBhEKDg8DCAoPEQgSEQ0RFRIPDQwGBAQGBAQGBgMGAwUIBBEIBgIIBwcEDwQWDgoNAgIV"
    "DBIUBQwOExUKFhURFRkWExEQAgICAgIDAgEEAwQICgIVDAkGDAoLBhMCGxIOEQUECQwGBBIKCAQEDQUFBgMEBQQGBxcXFBgWFBgY"
    "EhcSDg0UBQoNEAoMCxAEFAYICQsREg0JCgwDBQcMDgcPDQkOEQ4MCgkICAYJBwUJCQMIBAUHBQ4FAwEFBQUDDAUTCwcKAgMLDwcJ"
    "CAECBwkDCwkHCQwKBwcIDQ0LDgwKDg4IDQkEAwoKAgkHBgsKCQgKDgoKDAcIBAsGBBMMCwgDDgMDBwgCAwUGCBgYFhkXFRkZExgU"
    "Dw4VAwsOEQsNDBIEFQkGCgkTEwYKAgMOBgcGAwkEAwMGBgMCAgQTExEUEhAUFA4TDwoJEAQGCQwGCQgNAxAJBAYGDQ4ODwoMCAUG"
    "DA4CDw0JDhEOCwoKCAgHCQcHCQkHCQgDAggOBgkHBwsKCQwIEwsKDAYGChAKCBcPDggGEgYICwYFBgkKCxwcGh0bGR0dFxwYExIZ"
    "Bg8SFQ8REBYIGQUJDgoXFwQKBAQSCgkIAw0EAgUHAwUEBQYXFhQYFhQYGBIXEg4MFAUKDRAKDAsQBRQJBggJERIDBwQFDgoLCgQM"
    "BAMECgcFBQQEExIQFBIQFBQOEw4MDBAFCgkMBwgHDAYQDAEEAw0OBgsEAxIKCAYBDQMDBQUDAgMFBhcWFBgWFBgYEhcSDgwUAwoN"
    "EAoMCxADFAcFCAcREgUMBgYTDAoHAw4CAwcGAgQFBggYGBYZGBUZGRQZFA8OFgYMDhIMDQwSBhUIBQoIExMDBgMFDggLCgQLBAID"
    "CQYGBQQDExMRFBIQFBQOEw8KCxAFCAkMBggHDQYQCwQFBA0OBAwHBxQMCwoEDwMECAkDBQYHCBkZFxoYFhoaFBkVEA8WBgwPEgwO"
    "DRMHFgsGCwcUFAkNBAMPCAYDBAoGBgQCBQQDBAYUFBIVFBEWFRAVEAwKEgQICg4ICggOAhEHBwgKDxAICwUEEgsJBQQNBAQGBAMF"
    "BAYHFxcVGBcUGRgTGBMPDRUFCw0RCwwLEQQUBgcJChITFw4UFgcOEBUXCxgXExcbGBUTEgICBAEDBQEBBgEGCgwEFw4MCA4MDggV"
    "BB0UEBMHBhYNExUGDQ8UFgoXFhIWGhcUEhECAgMCAQQCAgUEBQkLBBYNCwcNCw0HFAQcEw8SBgUUCxETBAsNEhQJFRQQFBgVEhAP"
    "AgIBAgICAwIDAwMHCQIUCwkFCwoLBRICGhENEAQDFQwSFAUMDhMVChYVERUZFhMREAIBAgIBAwICBAMECAoDFQwKBgwLDAYTAxsS"
    "DhEFBBYNExQFDQ8UFgoXFRIWGRcUEhEBAgMBAgMBAQUBBAkKAxYNCgcNCwwHFAMbEw8SBgUTCxASAwoMEhMJFRMPExcUERAOAgMB"
    "AwIBAwMDAwIHCQIUCwgFCwkKBBICGREMEAMDEgoPEQIKCxETCRQSDhMWExAPDgMDAQQDAQQEAgMCBwkBEwoHBAoICQMRARgQCw8C"
    "AhIMDhAFCQoQEgYTEQ0SFRIQDg0FBAMFAwQFBQQFBAUGBBIJBwUJCQkGEAUXDwsOAwMTChARAgoMERMJFBMPExcUEQ8OAwMBBAIB"
    "BAQCAwIHCQITCgcECggJBBEBGBAMDwMDEQkOEAIJChASCBMRDRIVEhAODQQFAgUEAgUFAgQBBggCEgkGAwkHCAMQAhcPCg4CAQwL"
    "CQsFBAULDAUODAgNEA0KCQgJCQcKCAYKCgUJBgMFBg0EBQMEBwYFCwYSCgcJBAQJBgYIBwgKCQkKCwkFCg0KBwYEDAwKDQwJDQ0I"
    "DQgICgoJBwIGAwMCBgcJDwcEBgcHEwsQEgMLDBIUCRUTDxQXFBIQDwMCAQMCAgMDAwMDBwkCFAsIBQsJCgQSAhkRDBAEAwoLBggH"
    "AwUICgULCQYKDQoIBgYMDAoNCwkNDQcMCAQFCQoCBQUDBwYGCAkPBwYIBgcLCAgKBQYJCgsJDQsHCw8MCQgGCgoICwoHCwsGCwYH"
    "CQgLBQMEBQQFBAkHEQkHCAUFDQ4KDAcEBgsNBA8NCQ0RDgsKCAkIBwkIBwkJBgoHAQQHDQQIBgUKCQgLBxMMCgwFBQUGAwQLCAoJ"
    "BQsHBQIJCQcEAwEQEA4RDw0REQsQDAkKDQYHBgkEBQQKBQ0MAwIDCwsHBgQGCQgKCQcKCAcDCQsIBQQDDg4MEA4LEA8KDwoJCgwH"
    "BwUIBQQCCAYLDQQBBAkKBgcDAwwJCQgFCwYFAwgIBgMDBBERDxIQDhISDBENCwsOBQkHCgYGBQsEDgoDAwQMDAoKBwkHBAYICgYL"
    "CgYKDgsIBgcMCwkNCwgNDAcMBwYGCQoEBAUDBgUGCAkQBwUIBgcOBwsNAwoMDg4LEA4KDxIPDAsJBwcFCAYECAgDBwMJCgUPCQUE"
    "CQUFBA0EFAwHCwQECQkGBwgFCAcJCAoIBQkMCgcFBA0NCg4MCg4OCA0IBggKCQQDBgIFBAYHCg4GBAYHCA0KCQsEBQcLDQYODAkN"
    "EA4LCQgJCQcKCAYKCgUJBQQGBg0EBAQEBwYFCwYSCggKBAQKCQcJBgUHCAoIDAoGCg4LCAcFCwsJDAoIDAwHDAcFBwkKBAMFAgUE"
    "BQgIEAgGBwYGCQwEBQ0GBQQFCAcGBAUHBgMDBRISEBMRDxMTDRIOCQgPBgUICwcKCAwEDwkHBwkNDQIGBAYOCgwLBQwEAwQLBgYG"
    "BQQTExEUEhAUFA4TDwsMEAYJCQwHCAcNBxAMAgUDDg4GBQQFCwkLCgYLBwUDCQoIBQQDEA8NEQ8NERELEAsLCw0HCAYJBgUECQYN"
    "DAMCBAoLBQ4IBxYODAcFEQQGCQcCBAcJChsbGBwaGBwcFhsWEhEYBQ4RFA4QDxQHGAkIDAoVFgkLBQQLBgYEBggHBwQGCgcFBAUQ"
    "Dw0RDw0REQsQCwgIDQYGBgkEBwYJBA0LBgYICgsJCwUGCQQFBgcGCQcEBwsIBQQFDg4MDw0LDw8KDwoGBgwHBAYIAgcGCAULDQYH"
    "CAkJDBgREQkKCAMDBggICwICBgkEBhwaGRsZGhsYFRcUDQ4RDQ0LExARFhEOFgYNDAsMDAUSCwsKBAIHBQIJAgQFBwIDBwMVFBMV"
    "ExQVEQ4QDQcICgYGBgwJCg8LCBAFBwUHBwkGCAIEDAYIEQ4KDAgGDhAKCBEKDAoJCwkKCwoFCQcDAwoEBggFBAkGBgMHDwYHCQgM"
    "BQgBAg0GCBEOCgwIBg8RCggRCgwKCQsJCgsKBQkIAwILAwcIBQQKBgYCBg8GBwoIDAYMCQsEBwUNCwcGBgQLDQgFDQcPDg0PDQ0P"
    "CwgKBwkLBAkEAgYGBAkFCQoLBAMCAgIKAwUHDQwOFxQQDw4LFBYQDRcQBgQDBQMEBQQCBAIJCQYJCQsDBgUCBQgBFQkKCwoKCAQE"
    "BQwKDBUSDg4MCRMVDgsVDwgGBQcFBgcGAgUEBwcHCAgJAgQGAQMGAxMHCQoICQUPCAoDBgQKCAUEBAMICgQECgUSERASEBASDgsN"
    "CggKBwgEAgkGBwwICA0LBAIBAwQDDggIBwMDCwgECAIDCAsFAQsFEhAPEQ8QEQ4LDAkFBgcFAwMJBgYMBwYMCQMDBQQHDwIJCRIQ"
    "ExwZFBQTEBkbFREbFQICAwICAQEDBgQHDg0KDg4PCAsKBQkMBRkNDxAODwgUDQ4GBgQGAwQFBQcCBAMGBQIYFhUXFRYXFBETEAkL"
    "DQkJBw8MDRINChIICQgHCAgGDwkLBgUECgcFBgUDBwkFBQoEExEQEhAREg8MDgsICQgHBAUKBwgNCAgNCQYEBQMGBBAJCQUEAgkG"
    "BAUCBAYJBAMJAxQSERMREhMQDQ4LBwgJBwUDCwgIDgkHDgkFAwQEBQYPCQwDBgQMCAYDBAQICgYFCgUSERASEBESDgsNCgkKBwkE"
    "AwkHBwwICQ0LBgMEAwQLFxERCAoHBQQGBgcKAwIGCAQFGxkZGxgZGxcUFhMMDRAMDAsSDxAVEA4VCA0LCgsLAw4HCAgBAgsIBAgC"
    "AQgLBAMLBBIQDxEPEBEOCwwJBAYGBAMECQYGDAcFDAkDAwUECA4aFBQLDQsKCQsJCw0IBwsLBgseHBweGxweGhcZFhAQEw8PDhUS"
    "ExgTERgNEA4NDg4EEAoKCQIBCQYCCAIDBggCAggCFBIRExESExANDwwFBwkFBQULCAkOCQcOBgYEBgYIAw4HCAgCAgsIBAgDAggK"
    "BAMLBBIQDxEPEBEOCw0KBQYHBQMECQYHDAcFDAkDAwUFCA8DCQkSEBIbGRQUEhAZGxURGxUCAQIBAgICBAYEBw0NCg4ODwgLCgUJ"
    "DAQZDQ8QDg8QBAsLFBIUHRoWFhQRGx0WEx0XAQIDAQMCAgUIBgkPDwwQEBEJDAwHCw4GGw8REhAQDAEHBw8OEBkWEhEQDRYYEg8Z"
    "EgQDAgMBAgMEBAQECwoHCwsNBQgHAwcJAhcLDA0MDBAECwsTEhQdGhYVFBEaHRYTHRYBAgMBAwMCBQcFCA8OCw8PEQkMCwYLDgYb"
    "DxAREBAPAwoJEhETHBkVFBMQGRsVEhwVAgICAQICAQQGBAcODQoODhAICwoFCgwFGg4PEA8PDQEHBxAOERkXEhIQDhcZEw8ZEwMC"
    "AQMBAgMFBAQFCwsIDAwNBgkIAwcKAhcLDQ4MDQ0CCAgRDxEaFxMTEQ8YGhMQGhQDAgICAgICBAUDBgwMCQ0NDgYJCQQICwMYDA4P"
    "DQ0OAgkJEhASGxgUFBIPGRsUERsVAgICAQICAgQGBAcNDQoODg8HCgoFCQwEGQ0PEA4OCgMEBQ0LDRYUDw8NCxQWEAwWEAYFBAYE"
    "BQYGAgUECAgHCQkKAwYHAwUHAhQICgsJCgwBBggPDQ8YFhERDw0WGBIOGBIEAwMEAwIEAwMCBAoKBwsLDAUIBwMGCQIWCgwNCwwL"
    "AgUGDgwOFxUQEA4MFRcRDRcRBQQDBQMDBQUCBAMJCQYKCgsEBwYBBQgBFQkLDAoLCgYKDAsJCxQSDQ0LCRIUDQoUDgkHCAgIBwgE"
    "BwMECgwDCwcIBgcEBwUKBRIHCAkHBwsDBwgODA8XFRAQDgwVFxENFxEFBQQFBAMFBAMFBAkJBgoKCwQHBgQFCAQVCQsMCgsHBgYI"
    "CggKExEMDAoIERMNCRMNCQgHCQcHCQUDBAEGCAMHBgcCAwMEAgYEEQUHCAYHAg4HBwgBAgsIBAgCAgkLBAELBBIQDxEPEBEOCwwJ"
    "BAUHBAMECQYGDAcEDAkDAwUFCAUHBAYKBwkSDwsLCQYQEgsIEgwLCQgKCAkKCAMHBAYGBQYFBgIEBAQDBQUQBAYHBQcEDQcJBQQD"
    "DAkEBQMCCQsFAwwFEQ8OEA4PEA0KDAkHCQYHAgEIBQYLBgcLCgMBAgMEBg0ICwMGBQwKBwUFBAoMBwUMBhAPDhAODxAMCQsICQsF"
    "CQMCCAUFCgYJCwsEAwICAgULBwkFBQUOCwcGBQMLDgcFDgcPDQwODA0OCwgJBgcJBAcDAgYEBAkEBwkMAwMCAQQEDQYHCAIEDQoF"
    "CAQCCgwGBAwGEA4OEA4OEAwJCwgEBgYEAwQHBAYKBgUKCgMDBgQIAQwGBggDBA0KBgkEBAsNBgMNBhAODQ8NDg8LCQoHBAUHBAME"
    "BwQGCgUDCgsDAwUFCAUIBQcHBggRDgkJCAUOEAoHEQoMCgkLCQoLCAUHBAYHBAYDBQMCAwYCBQYPAwQFBAYECAMGCAYIEQ4KCggF"
    "DhEKBxEKDAoJCwkKCwgFBwQEBgYEAwUDAgUGAgQGDwMFBQQHCQMHCQwLDRYTDg4NChMVDwwWDwcFBAYEBQYDBAICCgoECggKBAUE"
    "BAUJAhQICQoJCQUKBwkHBgYPDAgIBgQMDwgGDwgODAsNCwwNCgcIBQgJBAgDAwUFAwgFBwgNAwMEBQQGEgsLBwQCBwQBBwIFBAcB"
    "AwcBFhQTFRMUFRIPEQ4HCAsHBwUNCgsQCwgQBwcGBQYHBA4ICQgDAwsIAwgDAggKBAQKBBIQEBIPEBIOCw0KBQcIBQQECQYIDAcG"
    "DAgEBAYECAsXEBAJCQcDAgUIBwkDAwUIBAQbGRgaGBkaFhMVEgwMDwsLChIPDxQQDRUGDAoJCwsEDQcJBQQEDQoFBQQCCgwGBAwG"
    "EA4OEA0OEAwJCwgHCQUHAgEHBAUKBgcKCwMBAgMEBgcFCAkHChMQCwsKBxASDAgSDAoICAoHCAoGBAUCBwgEBwUGAgIDBAIGBBAE"
    "BgcFBw=="
)
# ART_ERR[d][a][b] = side mismatch if tile b sits at TILE_DIRS[d] from tile a (d = 0..3)
ART_ERR = np.frombuffer(base64.b64decode("".join(_ART)), dtype=np.uint8).reshape(4, 49, 49).astype(float)

_NT = len(TILE_NAMES)
_ALL = (1 << _NT) - 1
BULK_MASK = sum(1 << i for i, k in enumerate(TILE_NAMES) if k[0] == "5")    # edg5xxx = main ground
PATCH_MASK = _ALL & ~BULK_MASK
HARD = 18          # side mismatch above this counts as a visible seam
SIGMA = 6.0        # smaller = stricter about matching sides
_cache = {}


def _allowed(d, dom):
    r = _cache.get((d, dom))
    if r is None:
        r = 0
        m = dom
        while m:
            b = m & -m
            r |= TILE_ADJ[d][b.bit_length() - 1]
            m ^= b
        _cache[(d, dom)] = r
    return r


def _cost(res, cell, nbr, t):
    """(broken rules, art mismatch) if `cell` holds tile t."""
    broken = 0
    art = 0.0
    for nb, d in nbr[cell]:
        o = res.get(nb)
        if o is None:
            continue
        if not (TILE_ADJ[d][t] >> o & 1):
            broken += 1
        if d < 4:
            art += ART_ERR[d][t][o]
    return broken, art


def _solve_tiles(cells, init, rng):
    import heapq
    dom = {c: init.get(c, _ALL) for c in cells}
    nbr = {c: [((c[0] + dx, c[1] + dy), i) for i, (dx, dy) in enumerate(TILE_DIRS)
               if (c[0] + dx, c[1] + dy) in dom] for c in cells}
    heap = []

    def push(c):
        heapq.heappush(heap, (bin(dom[c]).count("1"), rng.random(), c))

    def prop(stack):
        while stack:
            c = stack.pop()
            D = dom[c]
            for nb, d in nbr[c]:
                nd = dom[nb] & _allowed(d, D)
                if nd != dom[nb] and nd:            # dead end: skip, repaired below
                    dom[nb] = nd
                    stack.append(nb)
                    push(nb)

    for c in dom:
        prop([c])
    for c in dom:
        push(c)

    out = {}
    while heap:
        cnt, _, c = heapq.heappop(heap)
        if c in out:
            continue
        D = dom[c]
        if bin(D).count("1") != cnt:
            push(c)
            continue
        if cnt > 1:
            opts = [i for i in range(_NT) if D >> i & 1]
            w = []
            for t in opts:                           # prefer tiles whose sides match placed neighbours
                art = _cost(out, c, nbr, t)[1]
                w.append(TILE_WEIGHTS[t] * np.exp(-art / SIGMA))
            dom[c] = 1 << rng.choices(opts, w)[0]
        out[c] = dom[c].bit_length() - 1
        prop([c])

    # local repair: fix broken rules first, then visible seams
    for sweep in range(40):
        bad = [c for c in out if _cost(out, c, nbr, out[c])[0] or _cost(out, c, nbr, out[c])[1] > HARD * 2]
        if not bad:
            break
        rng.shuffle(bad)
        for c in bad:
            allow = init.get(c, _ALL)
            cur = _cost(out, c, nbr, out[c])
            curv = cur[0] * 60 + cur[1]
            best = None
            for t in range(_NT):
                if not allow >> t & 1:
                    continue
                b, a = _cost(out, c, nbr, t)
                v = (b * 60 + a, rng.random(), t)
                if best is None or v < best:
                    best = v
            if best[0] < curv:
                out[c] = best[2]
    return out


# ----------------------------------------------------------------------------
# Patch layout: separate organic blobs (like the real maps), not one big noisy mass
# ----------------------------------------------------------------------------
def _shift(a, dx, dy):
    out = np.zeros_like(a)
    h, w = a.shape
    out[max(0, dy):h + min(0, dy), max(0, dx):w + min(0, dx)] = a[max(0, -dy):h - max(0, dy), max(0, -dx):w - max(0, dx)]
    return out


def _erode(a):
    r = a.copy()
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            r &= _shift(a, dx, dy)
    return r


def _dilate(a):
    r = a.copy()
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            r |= _shift(a, dx, dy)
    return r


def blob_mask(m, seed, share, median=36, sigma=0.95, min_size=7, max_size=330, gap=2):
    """m x m bool, True = rough patch. Blobs are kept `gap` tiles apart, sizes like dgen's maps."""
    rng = np.random.default_rng(int(seed) + 99)
    target = share * m * m * 1.1
    occ = np.zeros((m, m), bool)
    block = np.zeros((m, m), bool)
    total = 0
    sizes = []
    while sum(sizes) < target * 1.3 and len(sizes) < 400:
        sizes.append(int(np.clip(rng.lognormal(np.log(median), sigma), min_size, max_size)))
    sizes.sort(reverse=True)
    for A in sizes:
        if total >= target:
            break
        for _ in range(60):
            cx, cy = rng.uniform(0, m, 2)
            aspect = rng.uniform(1.0, 2.2)
            th = rng.uniform(0, np.pi)
            b = np.sqrt(A / (np.pi * aspect))
            a = aspect * b
            ph = rng.uniform(0, 2 * np.pi, 3)
            R = int(a * 1.7) + 3                                  # work on a small window only
            x0, x1 = max(0, int(cx) - R), min(m, int(cx) + R + 1)
            y0, y1 = max(0, int(cy) - R), min(m, int(cy) + R + 1)
            yy, xx = np.mgrid[y0:y1, x0:x1]
            dx = xx - cx
            dy = yy - cy
            u = (dx * np.cos(th) + dy * np.sin(th)) / a
            v = (-dx * np.sin(th) + dy * np.cos(th)) / b
            phi = np.arctan2(v, u)
            lim = 1 + 0.25 * np.sin(2 * phi + ph[0]) + 0.2 * np.sin(3 * phi + ph[1]) + 0.12 * np.sin(5 * phi + ph[2])
            blob = np.hypot(u, v) <= lim
            if blob.sum() < min_size or (blob & block[y0:y1, x0:x1]).any():
                continue
            occ[y0:y1, x0:x1] |= blob
            total += int(blob.sum())
            X0, X1, Y0, Y1 = max(0, x0 - gap), min(m, x1 + gap), max(0, y0 - gap), min(m, y1 + gap)
            reg = occ[Y0:Y1, X0:X1].copy()
            for _ in range(gap):
                reg = _dilate(reg)
            block[Y0:Y1, X0:X1] |= reg
            break
    return _dilate(_erode(occ))              # drop 1-tile spikes


_mask_cache = {}



def ground_mask(n, seed, density):
    """n x n bool at hex resolution.
    True = main/light ground (edg5xxx).
    0.0 = all dark ground; 1.0 = all main/light ground.
    """
    density = max(0.0, min(1.0, float(density)))
    key = (int(n), int(seed), round(density, 3))

    if key not in _mask_cache:
        if len(_mask_cache) > 8:
            _mask_cache.clear()

        if density <= 0.0:
            mask = np.zeros((n, n), dtype=bool)
        elif density >= 1.0:
            mask = np.ones((n, n), dtype=bool)
        else:
            m = n // 2
            blobs = blob_mask(m, seed, 1.0 - density)
            mask = ~np.kron(blobs, np.ones((2, 2), dtype=bool))

        _mask_cache[key] = mask

    return _mask_cache[key]


def _drop_small(cells, patch, min_size=6):
    """Remove patch pieces smaller than min_size (8-connected) so no lonely edge tiles appear."""
    seen = set()
    out = set(patch)
    for c in patch:
        if c in seen:
            continue
        st = [c]
        seen.add(c)
        comp = []
        while st:
            p = st.pop()
            comp.append(p)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    q = (p[0] + dx, p[1] + dy)
                    if q in patch and q not in seen:
                        seen.add(q)
                        st.append(q)
        if len(comp) < min_size:
            out.difference_update(comp)
    return out


def build_tiles(m):
    """Fill m['tiles'] with (x, y, path). m['groundA'] (hex resolution, True = main ground) decides
    where the rough patches are; every patch tile is non-edg5xxx, everything else is edg5xxx."""
    import random
    cells = m["tile_cells"]
    ground = m["groundA"]
    seed = int(m["p"]["seed"])
    patch = _drop_small(cells, {c for c in cells if not ground[c[1] * 2, c[0] * 2]})
    init = {c: (PATCH_MASK if c in patch else BULK_MASK) for c in cells}
    res = _solve_tiles(cells, init, random.Random(seed * 7919 + 1))
    m["tiles"] = [(tx * 2, ty * 2, "art\\tiles\\edg" + TILE_NAMES[i] + ".frm")
                  for (tx, ty), i in sorted(res.items(), key=lambda kv: (kv[0][1], kv[0][0]))]
    return m["tiles"]


# ============================================================================
# MAP HEADER
# ============================================================================
HEADER = ("[Header]\r\nVersion\t4\r\nMaxHexX\t{n}\r\nMaxHexY\t{n}\r\nWorkHexX\t{w}\r\nWorkHexY\t{w}\r\n"
          "ScriptModule\t-\r\nScriptFunc\t-\r\nNoLogOut\t0\r\nTime\t0\r\nDayTime\t300  600  1140 1380\r\n"
          "DayColor0\t18  18  53\r\nDayColor1\t128 128 128\r\nDayColor2\t103 95  86\r\nDayColor3\t51  40  29\r\n\r\n")


# ============================================================================
# NOISE
# ============================================================================
def fractal_noise(n, seed, octaves, persistence):
    """n x n array in [0,1]."""
    rng = np.random.default_rng(seed)
    out = np.zeros((n, n))
    amp, total = 1.0, 0.0
    for o in range(max(1, octaves)):
        cells = 4 * 2 ** o
        g = rng.random((cells + 2, cells + 2))
        t = np.linspace(0, cells, n, endpoint=False)
        i = t.astype(int)
        f = t - i
        f = f * f * (3 - 2 * f)
        a = g[np.ix_(i, i)]
        b = g[np.ix_(i, i + 1)]
        c = g[np.ix_(i + 1, i)]
        d = g[np.ix_(i + 1, i + 1)]
        fx, fy = f[None, :], f[:, None]
        v = (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy
        out += v * amp
        total += amp
        amp *= persistence * 4 if persistence < 0.25 else persistence
    out /= total
    return (out - out.min()) / (out.max() - out.min() + 1e-9)


# ============================================================================
# MAP BOUNDS
# ============================================================================
def bounds(n):
    """Playable rectangle in skewed hex space (u = y + x/2, v = y - 1.5x)."""
    import math
    umin = math.floor(0.25 * n + 0.25)
    vmin = math.ceil(-0.75 * n + 0.25)
    return umin, umin + n - 0.5, vmin, vmin + n - 0.5


def inside(x, y, n):
    a, b, c, d = bounds(n)
    u = y + x / 2.0
    v = y - 1.5 * x
    return (u >= a) & (u <= b) & (v >= c) & (v <= d)


def inside_tiles(x, y, n):
    """Slightly looser region for ground tiles."""
    a, b, c, d = bounds(n)
    u = y + x / 2.0
    v = y - 1.5 * x
    return (u >= a - 2) & (u <= b + 0.5) & (v >= c - 1) & (v <= d + 2.5)


# scroll blockers (reproduces dgen exactly)
BLOCK_EVEN = [(-1, 0), (-1, 1), (0, 1), (1, 0)]
BLOCK_ODD = [(-1, -1), (-1, 0), (0, 1), (1, -1)]


# ============================================================================
# MAP GENERATION
# ============================================================================
def generate(p):
    """Generate map tiles layout and objects."""
    p = {**DEFAULTS, **p}
    n = int(p["size"]) // 2 * 2
    if n < 10:
        raise ValueError("Can't be less than ten.")
    rng = np.random.default_rng(p["seed"] + 1)
    noise = fractal_noise(n, p["seed"], int(p["octaves"]), p["persistence"])
    ys, xs = np.mgrid[0:n, 0:n]
    dele = p["delete_outside"]
    ins = inside(xs, ys, n) if dele else np.ones((n, n), bool)
    tins = inside_tiles(xs, ys, n) if dele else np.ones((n, n), bool)
    groundA = ground_mask(n, p["seed"], p["density"])        # True = main ground, False = rough patch
    P = p["protos"]
    tile_cells = {(x // 2, y // 2) for y in range(0, n, 2) for x in range(0, n, 2)
                  if tins[y, x] and (not dele or ins[y, x])}
    taken, objs = set(), []

    def put(proto, x, y):
        if 0 <= x < n and 0 <= y < n and (x, y) not in taken and (not dele or ins[y, x]):
            taken.add((x, y))
            objs.append((proto, x, y))
            return True
        return False

    def pick(k):
        L = P[k]
        return int(L[rng.integers(len(L))])

    if p["scroll_blockers"]:                                  # one-hex line along the border
        pad = np.pad(ins, 1, constant_values=False)
        out_e = np.zeros_like(ins)
        out_o = np.zeros_like(ins)
        for (dx, dy), acc in [(o, out_e) for o in BLOCK_EVEN] + [(o, out_o) for o in BLOCK_ODD]:
            acc |= ~pad[1 + dy:1 + dy + n, 1 + dx:1 + dx + n]
        out = np.where(xs % 2 == 0, out_e, out_o)
        for y, x in zip(*np.nonzero(ins & out)):
            put(P["blocker"], int(x), int(y))

    r = rng.random((n, n))
    clump = np.clip(fractal_noise(n, p["seed"] + 7, 3, 0.5) ** 2 * 4.0, 0, 1)
    rc = r / np.maximum(clump, 1e-3)
    rg = rc / np.where(groundA, 1.0, max(p["patch_grass"], 1e-3))      # grass denser on patches
    for y in range(n):
        for x in range(n):
            if not ins[y, x]:
                continue
            v = noise[y, x]
            if r[y, x] < p["corn"] and 0.20 <= v <= 0.75:
                put(pick("corn"), x, y)
            elif rc[y, x] < p["dry_trees"] and v < 0.40:
                put(pick("dry_trees"), x, y)
            elif p["trees_min"] <= v <= p["trees_max"] and rc[y, x] < p["trees"]:
                put(pick("trees"), x, y)
            elif rc[y, x] < p["rocks"]:
                put(pick("rocks"), x, y)
            elif rc[y, x] < p["cactuses"] and v < 0.75:
                put(pick("cactuses"), x, y)
            elif p["grass_min"] <= v <= p["grass_max"] and rg[y, x] < p["grass"]:
                put(pick("grass"), x, y)
            elif rc[y, x] < p["misc"]:
                put(pick("misc"), x, y)
            elif r[y, x] < p["barrels"]:
                put(pick("barrels"), x, y)
    return dict(tiles=None, tile_cells=tile_cells, objects=objs, n=n, noise=noise,
                groundA=groundA, ins=ins, p=p)


# ============================================================================
# WRITE FOMAP
# ============================================================================
def write_fomap(m, path):
    if m["tiles"] is None:
        build_tiles(m)
    s = [HEADER.format(n=m["n"], w=m["n"] // 2), "[Tiles]\r\n"]
    s += [f"tile \t {x} \t {y} \t {t}\r\n" for x, y, t in m["tiles"]]
    s.append("\r\n[Objects]\r\n")
    s += [f"MapObjType\t2\r\nProtoId\t{pr}\r\nMapX\t{x}\r\nMapY\t{y}\r\n\r\n" for pr, x, y in m["objects"]]
    with open(path, "w", newline="", encoding="latin1") as f:
        f.write("".join(s))


# ============================================================================
# PREVIEW
# ============================================================================
def render(m, zoom=3, rot=0, w=None):
    """RGB preview, playable area resampled into an upright rectangle."""
    n = m["n"]
    P = m["p"]["protos"]
    img = np.zeros((n, n, 3), np.uint8)
    img[m["groundA"]] = (146, 108, 80)
    img[~m["groundA"]] = (122, 112, 72)
    img[~m["ins"]] = (40, 40, 40)
    col = {}
    if "blocker" in P:
        col[P["blocker"]] = (245, 245, 245)
    color_map = dict(corn=(210, 180, 70), dry_trees=(105, 78, 48), trees=(28, 62, 36),
                     rocks=(80, 78, 76), cactuses=(45, 105, 55), grass=(205, 170, 105),
                     misc=(105, 82, 58), barrels=(115, 82, 48))
    for k, c in color_map.items():
        for item in P.get(k, []):
            col[item[0] if isinstance(item, (list, tuple)) else item] = c
    for pr, x, y in m["objects"]:
        img[y, x] = col.get(pr, (255, 0, 255))
    w = w or int(n * 1.3 * ASPECT)
    h = int(w / ASPECT)
    U = np.linspace(0.25 * n, 1.25 * n, h)[:, None]
    V = np.linspace(-0.75 * n, 0.25 * n, w)[None, :]
    X = np.rint((U - V) / 2).astype(int)
    Y = np.rint(U - X / 2).astype(int)
    ok = (X >= 0) & (X < n) & (Y >= 0) & (Y < n)
    out = np.full((h, w, 3), 40, np.uint8)
    out[ok] = img[Y[ok], X[ok]]
    out = np.rot90(out, rot)
    out = np.repeat(np.repeat(out, zoom, 0), zoom, 1)
    return np.ascontiguousarray(out)


# ============================================================================
# GUI
# ============================================================================
def gui():
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

    root = tk.Tk()
    root.title("MapGen9000")
    root.geometry("1280x720")
    cfg = {k: v for k, v in DEFAULTS.items()}
    vars_ = {}

    holder = ttk.Frame(root)
    holder.pack(side="left", fill="y")
    sc = tk.Canvas(holder, width=400, highlightthickness=0)
    bar = ttk.Scrollbar(holder, orient="vertical", command=sc.yview)
    sc.configure(yscrollcommand=bar.set)
    bar.pack(side="right", fill="y")
    sc.pack(side="left", fill="y")
    side = ttk.Frame(sc, padding=6)
    sc.create_window((0, 0), window=side, anchor="nw")
    side.bind("<Configure>", lambda e: sc.configure(scrollregion=sc.bbox("all")))
    root.bind_all("<MouseWheel>", lambda e: sc.yview_scroll(-1 if e.delta > 0 else 1, "units"))
    view = tk.Frame(root, bg="#222")
    view.pack(side="right", expand=True, fill="both")
    canvas = tk.Label(view, bg="#222")
    canvas.place(relx=0.5, rely=0.5, anchor="center")
    state = {}
    job = {"id": None}

    sliders = [
        ("size", 20, 400, 2),
        ("seed", 0, 99999, 1),
        ("octaves", 1, 8, 1),
        ("persistence", 0.05, 0.9, 0.01),

        # Asset percentages: 0–100%
        ("density", 0, 100, 0.1),
        ("corn", 0, 100, 0.1),
        ("dry_trees", 0, 100, 0.1),
        ("trees", 0, 100, 0.1),
        ("rocks", 0, 100, 0.1),
        ("cactuses", 0, 100, 0.1),
        ("grass", 0, 100, 0.1),
        ("misc", 0, 100, 0.1),
        ("barrels", 0, 100, 0.1),

        ("patch_grass", 1, 6, 0.1),

        # Min/max distribution controls
        ("grass_min", 0, 1, 0.01),
        ("grass_max", 0, 1, 0.01),
        ("trees_min", 0, 1, 0.01),
        ("trees_max", 0, 1, 0.01),
    ]

    percentage_keys = {
        "density", "corn", "dry_trees", "trees", "rocks",
        "cactuses", "grass", "misc", "barrels"
    }

    range_keys = {
        "grass_min", "grass_max", "trees_min", "trees_max"
    }

    names = {
        "dry_trees": "Dry trees",
        "trees_min": "Trees minimum",
        "trees_max": "Trees maximum",
        "grass_min": "Grass minimum",
        "grass_max": "Grass maximum",
        "patch_grass": "Grass patch multiplier",
        "octaves": "Noise octaves",
        "persistence": "Noise persistence",
        "density": "Main ground density",
    }

    def display_name(k):
        return names.get(k, k.replace("_", " ").title())

    def display_value(k, value):
        if k in percentage_keys:
            return f"{value:.1f}%"
        if k in range_keys:
            return f"{value * 100:.0f}%"
        if k in ("size", "seed", "octaves"):
            return str(int(value))
        if k == "patch_grass":
            return f"{value:.1f}x"
        return f"{value:.2f}"

    def params():
        p = {}
        for k, v in vars_.items():
            value = v.get()
            if k in percentage_keys:
                value = value / 100.0
            p[k] = value
        for k in ("size", "seed", "octaves"):
            p[k] = int(p[k])
        p["protos"] = cfg["protos"]
        return p

    def update():
        job["id"] = None
        try:
            m = generate(params())
            state["m"] = m
            vw, vh = view.winfo_width(), view.winfo_height()
            w = max(120, int(min(vw, vh * ASPECT)) - 12) if vw > 100 else 450
            a = render(m, 1, 0, w=w)
            ppm = b"P6\n%d %d\n255\n" % (a.shape[1], a.shape[0]) + a.tobytes()
            state["img"] = tk.PhotoImage(data=ppm, format="PPM")
            canvas.config(image=state["img"])
            root.title(f"MapGen9000 - {len(m['tile_cells'])} tiles, {len(m['objects'])} objects")
        except Exception as e:
            root.title(f"MapGen9000 - {e}")

    def refresh(*_):
        if job["id"] is not None:
            try:
                root.after_cancel(job["id"])
            except Exception:
                pass
        job["id"] = root.after(150, update)

    def make_slider(parent, k, lo, hi, st, row, column):
        cell = ttk.Frame(parent)
        cell.grid(row=row, column=column, padx=4, sticky="w")
        header = ttk.Frame(cell)
        header.pack(fill="x")
        ttk.Label(header, text=display_name(k)).pack(side="left")
        value_label = ttk.Label(header, width=7, anchor="e")
        value_label.pack(side="right")
        v = tk.DoubleVar(value=DEFAULTS[k] * 100 if k in percentage_keys else DEFAULTS[k])
        vars_[k] = v

        def update_label(*_):
            value_label.config(text=display_value(k, v.get()))

        tk.Scale(cell, from_=lo, to=hi, resolution=st, orient="horizontal", length=170, variable=v,
                 command=lambda _: (update_label(), refresh())).pack()
        update_label()

    for i, (k, lo, hi, st) in enumerate(sliders):
        make_slider(side, k, lo, hi, st, i // 2, i % 2)
    r0 = (len(sliders) + 1) // 2

    for j, (key, label) in enumerate((("delete_outside", "Delete outside"), ("scroll_blockers", "Scroll blockers"))):
        var = tk.BooleanVar(value=DEFAULTS[key])
        vars_[key] = var
        ttk.Checkbutton(side, text=label, variable=var, command=refresh).grid(row=r0, column=j, sticky="w")

    def save():
        f = filedialog.asksaveasfilename(defaultextension=".fomap", filetypes=[("FOnline map", "*.fomap")])
        if f and "m" in state:
            write_fomap(state["m"], f)
            messagebox.showinfo("MapGen9000", "Saved " + f)

    def save_preset():
        f = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("MapGen9000 preset", "*.json")])
        if f:
            with open(f, "w") as fp:
                json.dump(params(), fp, indent=1)

    def load_preset():
        f = filedialog.askopenfilename(filetypes=[("MapGen9000 preset", "*.json")])
        if not f:
            return
        with open(f) as fp:
            d = json.load(fp)
        for k, v in vars_.items():
            if k in d:
                value = d[k]
                if k in percentage_keys:
                    value *= 100.0
                v.set(value)
        if "protos" in d:
            cfg["protos"] = d["protos"]
        refresh()

    def random_desert():
        rng = np.random.default_rng()
        vars_["seed"].set(int(rng.integers(0, 100000)))
        for k in ("corn", "dry_trees", "trees", "barrels"):
            vars_[k].set(0)
        vars_["cactuses"].set(rng.uniform(2.5, 5.0))
        vars_["rocks"].set(rng.uniform(0.5, 1.5))
        vars_["grass"].set(rng.uniform(0.2, 1.0))
        vars_["misc"].set(rng.uniform(0.5, 1.5))
        refresh()

    ttk.Button(side, text="Random Desert", command=random_desert).grid(
        row=r0 + 1, column=0, columnspan=2, sticky="ew", pady=(8, 4))
    ttk.Button(side, text="Save Preset", command=save_preset).grid(row=r0 + 2, column=0, sticky="ew", padx=(0, 2), pady=2)
    ttk.Button(side, text="Load Preset", command=load_preset).grid(row=r0 + 2, column=1, sticky="ew", padx=(2, 0), pady=2)
    tk.Button(side, text="Save .fomap", command=save, font=("TkDefaultFont", 9, "bold")).grid(
        row=r0 + 3, column=0, columnspan=2, sticky="ew", pady=(4, 2))

    view.bind("<Configure>", refresh)
    update()
    root.mainloop()


# ============================================================================
# CLI
# ============================================================================
if __name__ == "__main__":
    try:
        ap = argparse.ArgumentParser(prog="MapGen9000")
        ap.add_argument("--cli", metavar="OUT.fomap")
        ap.add_argument("--preset")
        for k, v in DEFAULTS.items():
            if isinstance(v, (int, float, str)) and not isinstance(v, bool):
                ap.add_argument("--" + k, type=type(v))
        a = ap.parse_args()
        if a.cli:
            p = json.load(open(a.preset)) if a.preset else {}
            p.update({k: v for k, v in vars(a).items() if k not in ("cli", "preset") and v is not None})
            m = generate(p)
            write_fomap(m, a.cli)
            print(f"{a.cli}: {len(m['tile_cells'])} tiles, {len(m['objects'])} objects")
        else:
            gui()
    except Exception:
        import traceback
        traceback.print_exc()
        input("\nPress Enter to close...")
