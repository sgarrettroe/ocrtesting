#!/bin/bash
N_PAGES_PER_SUBMISSION=$1
shift
for x in "$@"
do
    val=`gs --permit-file-read=$x -q -dNODISPLAY -c "($x) (r) file runpdfbegin pdfpagecount = quit"`;
    echo "$x: $val pages -> $(($val/$N_PAGES_PER_SUBMISSION)) submissions remainder $(($val%$N_PAGES_PER_SUBMISSION))"
done
