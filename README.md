# Web app
https://sgarrettroe.github.io/ocrtesting

https://sgarrettroe.github.io/ocrtesting/splitter


#
ocr process exams

# notes from earlier

see https://www.ghostscript.com/blog/ocr.html
https://ghostscript.com/doc/9.55.0/Devices.htm#OCR-Devices
```
export TESSDATA_PREFIX=/my/tesseract/data/
gs --permit-file-read=/my/tesseract/data/ -sDEVICE=ocr -o OutputFile=out.txt in.pdf

# crop small section of pdf for faster ocr 
gs -o multicrop.pdf -sDEVICE=pdfwrite -g700x500 -c "<</PageOffset [-30 -25]>> setpagedevice" -f multibatch.pdf
# do the ocr and output to separate txt files with page number in the name
~/Downloads/ghostscript-9.55.0/bin/gs --permit-file-read=$TESSDATA_PREFIX -sDEVICE=ocr -o multicrop-ocr-%03d.txt -r600 -dDownScaleFactor=3 multicrop.pdf

# python script guessing based on page order
python process_scans2.py <batch-000.pdf>

# count pages in a batch
for x in originals/SGR_v0_001.pdf ; do echo $x: `mdls -raw -name kMDItemNumberOfPages $x` ; done

# count pages in assessments
for x in A*_SGR_v0_001.pdf ; do echo $x: `mdls -raw -name kMDItemNumberOfPages $x` ; done
README (END)
```

