/*
MGRS lettering tables (generated).

This file is GENERATED. The generator tools/validation/gen_mgrs_tables.py
writes it from the validated source under data/mgrs/. Do not edit it by
hand. Edit the source and regenerate it.

The rows are, in order:

  0  band letters, C to X omitting I and O (20 letters, band 0 is 80 S)
  1  column letter sets, indexed by (zone - 1) mod 3
  2  row letters, A to V omitting I and O (20 letters, row 0 is A)
  3  even-zone row offset, the AA scheme shift (odd zones start at A)
  4  zone strings, "01" to "60"
  5  digit characters, "0" to "9"

The lettering is defined by DMA TM 8358.1, DMA TM 8358.2 and the NGA
MGRS guidance (Modified February 2009). No letter is invented: every
letter here is one of those sources.
*/
[
    ["C", "D", "E", "F", "G", "H", "J", "K", "L", "M", "N", "P", "Q", "R", "S", "T", "U", "V", "W", "X"],
    [["A", "B", "C", "D", "E", "F", "G", "H"], ["J", "K", "L", "M", "N", "P", "Q", "R"], ["S", "T", "U", "V", "W", "X", "Y", "Z"]],
    ["A", "B", "C", "D", "E", "F", "G", "H", "J", "K", "L", "M", "N", "P", "Q", "R", "S", "T", "U", "V"],
    5,
    ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28", "29", "30", "31", "32", "33", "34", "35", "36", "37", "38", "39", "40", "41", "42", "43", "44", "45", "46", "47", "48", "49", "50", "51", "52", "53", "54", "55", "56", "57", "58", "59", "60"],
    ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
]
