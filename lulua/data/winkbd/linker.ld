/* taken from https://github.com/reactos/reactos/blob/893a3c9d030fd8b078cbd747eeefd3f6ce57e560/dll/keyboard/kbdlayout.lds */
SECTIONS
{
  .data __image_base__ + __section_alignment__ :
  {
    *(.data)
    *(SORT(.data*))
    *(.rdata)
    *(SORT(.rdata*))
    *(.text)
    *(SORT(.text*))
    *(.bss)
    *(COMMON)
  }

  .rsrc BLOCK(__section_alignment__) :
  {
    *(.rsrc)
    *(SORT(.rsrc*))
  }

  .reloc BLOCK(__section_alignment__) :
  {
    *(.reloc)
  }

  .edata BLOCK(__section_alignment__) :
  {
    *(.edata)
  }

  /DISCARD/ :
  {
    *(*)
  }
}
