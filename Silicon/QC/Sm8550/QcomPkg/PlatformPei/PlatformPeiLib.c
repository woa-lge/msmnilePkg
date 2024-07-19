/** @file

  Copyright (c) 2011-2014, ARM Limited. All rights reserved.
  Copyright (c) 2014, Linaro Limited. All rights reserved.
  Copyright (c) 2023, DuoWoA Authors. All rights reserved.

  SPDX-License-Identifier: BSD-2-Clause-Patent


  NOTICE:
    Some Addresses, Protocols, Functions and Guids are got from decompile tools.

**/

#include <PiPei.h>

#include <Library/DebugLib.h>
#include <Library/HobLib.h>
#include <Library/MemoryAllocationLib.h>
#include <Library/PcdLib.h>
#include <Protocol/EFIKernelInterface.h>
#include "PlatformPeiLibInternal.h"
#include "EFIDTBExtnProtocol.h"

STATIC
EFI_STATUS
CfgGetMemInfoByName(
    CHAR8 *RegionName, ARM_MEMORY_REGION_DESCRIPTOR_EX *MemRegions)
{
  return LocateMemoryMapAreaByName(RegionName, MemRegions);
}

STATIC
EFI_STATUS
CfgGetMemInfoByAddress(
    UINT64 RegionBaseAddress, ARM_MEMORY_REGION_DESCRIPTOR_EX *MemRegions)
{
  return LocateMemoryMapAreaByAddress(RegionBaseAddress, MemRegions);
}

STATIC
EFI_STATUS
CfgGetCfgInfoString(CHAR8 *Key, CHAR8 *Value, UINTN *ValBuffSize)
{
  if (AsciiStriCmp(Key, "OsTypeString") == 0) {
    AsciiStrCpyS(Value, *ValBuffSize, "WP");
    return EFI_SUCCESS;
  }

  return EFI_NOT_FOUND;
}

STATIC
EFI_STATUS
CfgGetCfgInfoVal(CHAR8 *Key, UINT32 *Value)
{
  return LocateConfigurationMapUINT32ByName(Key, Value);
}

STATIC
EFI_STATUS
CfgGetCfgInfoVal64(CHAR8 *Key, UINT64 *Value)
{
  return LocateConfigurationMapUINT64ByName(Key, Value);
}

STATIC
UINTN
SFlush(VOID) { return EFI_SUCCESS; }

STATIC
UINTN
SControl(IN UINTN Arg, IN UINTN Param) { return EFI_SUCCESS; }

STATIC
BOOLEAN
SPoll(VOID) { return TRUE; }

STATIC
UINTN
SDrain(VOID) { return EFI_SUCCESS; }

STATIC
EFI_STATUS
ShInstallLib(IN CHAR8 *LibName, IN UINT32 LibVersion, IN VOID *LibIntf)
{
  return EFI_SUCCESS;
}

UefiCfgLibType ConfigLib = {0x00010002,          CfgGetMemInfoByName,
                            CfgGetCfgInfoString, CfgGetCfgInfoVal,
                            CfgGetCfgInfoVal64,  CfgGetMemInfoByAddress};

SioPortLibType SioLib = {
    0x00010001, SerialPortRead, SerialPortWrite, SPoll,
    SDrain,     SFlush,         SControl,        SerialPortSetAttributes,
};

STATIC
EFI_STATUS
ShLoadLib(CHAR8 *LibName, UINT32 LibVersion, VOID **LibIntf)
{
  if (LibIntf == NULL)
    return EFI_NOT_FOUND;

  if (AsciiStriCmp(LibName, "UEFI Config Lib") == 0) {
    *LibIntf = &ConfigLib;
    return EFI_SUCCESS;
  }

  if (AsciiStriCmp(LibName, "SerialPort Lib") == 0) {
    *LibIntf = &SioLib;
    return EFI_SUCCESS;
  }

  return EFI_NOT_FOUND;
}

ShLibLoaderType ShLib = {0x00010001, ShInstallLib, ShLoadLib};

STATIC
VOID BuildMemHobForFv(IN UINT16 Type)
{
  EFI_PEI_HOB_POINTERS      HobPtr;
  EFI_HOB_FIRMWARE_VOLUME2 *Hob = NULL;

  HobPtr.Raw = GetHobList();
  while ((HobPtr.Raw = GetNextHob(Type, HobPtr.Raw)) != NULL) {
    if (Type == EFI_HOB_TYPE_FV2) {
      Hob = HobPtr.FirmwareVolume2;
      /* Build memory allocation HOB to mark it as BootServicesData */
      BuildMemoryAllocationHob(
          Hob->BaseAddress, EFI_SIZE_TO_PAGES(Hob->Length) * EFI_PAGE_SIZE,
          EfiBootServicesData);
    }
    HobPtr.Raw = GET_NEXT_HOB(HobPtr);
  }
}

STATIC GUID gEfiInfoBlkHobGuid   = EFI_INFORMATION_BLOCK_GUID;
STATIC GUID gFvDecompressHobGuid = EFI_FV_DECOMPRESS_GUID;
STATIC GUID gEfiShLibHobGuid     = EFI_SHIM_LIBRARY_GUID;
STATIC GUID gEfiSchedIntfGuid    = EFI_SCHED_INTF_GUID;
STATIC GUID gEfiSecDtbGuid       = EFI_SEC_DTB_GUID;

VOID InstallPlatformHob()
{
  static int initialized = 0;

  if (!initialized) {
    ARM_MEMORY_REGION_DESCRIPTOR_EX InfoBlk;
    LocateMemoryMapAreaByName("Info Blk", &InfoBlk);
    UINTN Data3 = 0xC5D47000; // FV2 Address
    UINTN InfoBlkAddress = InfoBlk.Address;
    UINTN ShLibAddress   = (UINTN)&ShLib;
    EFI_KERNEL_PROTOCOL   *SchedIntf       = (VOID *)PcdGet64(KernelProtocolAddress);
    EFI_DTB_EXTN_PROTOCOL *DTBExtnProtocol = (VOID *)PcdGet64(XBLDTProtocolAddress);

    BuildMemHobForFv(EFI_HOB_TYPE_FV2);
    BuildGuidDataHob(
        &gEfiInfoBlkHobGuid, &InfoBlkAddress, sizeof(InfoBlkAddress));
    BuildGuidDataHob(&gEfiShLibHobGuid, &ShLibAddress, sizeof(ShLibAddress));
    BuildGuidDataHob(&gFvDecompressHobGuid, &Data3, sizeof(Data3));
    BuildGuidDataHob(&gEfiSchedIntfGuid, &SchedIntf, sizeof(SchedIntf));            // Schedule Interface
    BuildGuidDataHob(&gEfiSecDtbGuid, &DTBExtnProtocol, sizeof(DTBExtnProtocol));   // XBL DT

    initialized = 1;
  }
}

EFI_STATUS
EFIAPI
PlatformPeim(VOID)
{

  BuildFvHob(PcdGet64(PcdFvBaseAddress), PcdGet32(PcdFvSize));

  InstallPlatformHob();

  return EFI_SUCCESS;
}
