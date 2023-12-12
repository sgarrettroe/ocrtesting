import subprocess
import sys
import os
#import glob
from pathlib import Path #for sorting paths below (supercedes glob)
from random import uniform
from random import randrange   # Integers - Note randrange(a,b) b is NOT included
from random import randint     # Integers - Note randint(a,b) b is included
from random import choice      # flip = choice([0,2])
from random import sample
from random import shuffle
import periodictable as pt
import pymatgen.core as mg
from scipy.constants import N_A
from scipy.constants import h
from scipy.constants import c
from scipy.constants import Rydberg
from scipy.special import comb
from chempy import balance_stoichiometry
from chempy import Substance
from fractions import Fraction
from dataclasses import dataclass, field
import numpy as np
import string
import logging
import re #regular expressions (needed searching for bond angles in chemFigString)
from itertools import permutations #used in chemFigString to generate resonance structure permutations
from string import Template #used in A23C

#set up logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# path to gs >= 9.54
gscmd = '/Users/SGR/Downloads/ghostscript-9.55.0/bin/gs'

# path to tessdata files
TESSDATA_PREFIX = '/Users/SGR/Downloads/tessdata_fast-main/'

# environmental variable
my_env = os.environ.copy()
my_env["TESSDATA_PREFIX"] = TESSDATA_PREFIX

def cropcorner(pdfin) -> None:
    """Crop the corner of the pdf file to extract the assessment name"""
    logging.info(f'\t...cropping {pdfin} to crop_{pdfin}')
    #first try lower left of pdf (not scan)
    #sizestr = '700x500'
    #offsetstr = '-30 -25'

    #second try lower left of scans
    #sizestr = '700x500'
    #offsetstr = '-45 -60'

    #third try title
    sizestr = '1700x500'
    offsetstr = '-45 -700'
    
    x = subprocess.run([gscmd,'-q','-o','crop_'+pdfin,'-sDEVICE=pdfwrite',f'-g{sizestr}','-c',f'"<</PageOffset [{offsetstr}]>> setpagedevice"','-f',pdfin])
    
    return None

def ocrcorner(pdfin) -> None:
    """run ocr on the cropped corner"""
    logging.info(f'\t...running OCR on crop_{pdfin}')
    x = subprocess.run([gscmd,'-q','-o','crop_'+pdfin+'-%03d.txt','--permit-file-read=$TESSDATA_PREFIX','-sDEVICE=ocr','-r600','-dDownScaleFactor=3','crop_'+pdfin],env=my_env)
    return None

def buildpagelist2(pdfin):
    logging.info(f'\t...build list of assessments')

    asslist = ['5.1', '1.1','1.2','1.3','2.1','2.2','2.3','2.3','3.1','3.2','3.3','4.1','4.2','4.3']
    pageassdict = {}
    oldassnumber = '5.1' #first page
    oldpagenumber = 0

    for file in sorted(Path('.').glob(f'crop_{pdfin}-*.txt')):
        #m = re.search(r'.*pdf-(\d+).txt',file)
        pagenumber = re.findall(r'(?<=pdf-)\d+(?=\.txt)',str(file))
        logging.debug(pagenumber)
        
        fid = open(file,'r')
        ocrtext = fid.read()
        fid.close()
        logging.debug(ocrtext)
        ## search for assessment by A3.2v template
        ##m = re.search(r'A(\d.\d)v',file)
        #assnumber = re.findall(r'\d\.\d(?=[abc]v\d+)',ocrtext)

        # search for assessment by "Assessment 3.2a" template
        
        assnumber = re.findall(r'(?<=ment )\d\.[\dl]',ocrtext)
        if not assnumber:
            assnumber = re.findall(r'(?<=ment \\)\d\.[\dl]',ocrtext)
        if not assnumber:
            assnumber = re.findall(r'(?<=ment. )\d\.[\dl]',ocrtext)

        if not assnumber:
            assnumber = [asslist[(int(pagenumber[0])-1)%len(asslist)]]
            logging.warning('GUESSING ' + str(pagenumber) +' is ' + str(assnumber))
        if assnumber:
            #logging.warning(print(assnumber))
            if assnumber[-1][-1]=='l':
                assnumber[-1]=assnumber[-1][:-1] + '1'

            logging.info('\t...page ' + str(pagenumber) + ' assessment ' + str(assnumber))
            pageassdict[int(pagenumber[0])]=assnumber[0]
            oldassnumber = assnumber[0]
        else:
            #logging.warning('\t...page ' + str(pagenumber) + ' assuming same as previous page ' + str([oldassnumber]) + '**************')
            logging.warning('\t...page ' + str(pagenumber))
            assnumber = input('What is the assessment for:\n' + ocrtext +'\n:\n') 
            #pageassdict[int(pagenumber[0])]=oldassnumber

    logging.debug(pageassdict)

    flipped = {}
    for key, value in pageassdict.items():
        if value not in flipped:
            flipped[value] = [key]
        else:
            flipped[value].append(key)

    logging.debug(flipped)
    return flipped

def processAssessment(pdfin,assessmentdict):
    logging.info('\t...extracting pages')
    for key in assessmentdict:
        assName = 'A'+key+'_'+pdfin
        logging.debug(assName)
        value = assessmentdict[key]
        #must be in increasing order so sort, then make strings, then combine with comma sep
        value.sort() #sorts in place        
        tmp = [str(num) for num in value]
        pagelist = ','.join(tmp)
        logging.debug('Page list = ' + pagelist+'\n\nCOMMAND:\n')
        logging.debug(' '.join([gscmd,'-q','-o',assName,'-sPageList='+pagelist,'-sDEVICE=pdfwrite',pdfin]))
        x = subprocess.run([gscmd,'-q','-o',assName,'-sPageList='+pagelist,'-sDEVICE=pdfwrite',pdfin])
    return None

def cleanup(pdfin):
    logging.info('\t...cleaning up')

    dirdict = {}
    dirdict['originals'] =  Path('./originals')
    #dirdict['processed'] =  Path('./processed')
    dirdict['cropped'] =  Path('./cropped')
    dirdict['ocrtxt'] = Path('./ocrtxt')

    for p in dirdict.values():
        if p.is_dir():
            logging.debug(f'\t...found dir {p}')
        else:
            logging.debug(f'\t...making dir {p}')
            p.mkdir()
            
    # remove all temp files
    for file in sorted(Path('.').glob(f'crop_{pdfin}-*.txt')):
        #file.unlink() 
        destination = dirdict['ocrtxt'] / file
        file.replace(destination)
        
    
    # move processed pdf to originals directory
    source = Path(pdfin)
    destination = dirdict['originals'] / pdfin
    source.replace(destination)

    #move cropped pages to processed directory
    for file in sorted(Path('.').glob(f'crop_{pdfin}')):
        destination = dirdict['cropped'] / file
        file.replace(destination)

    

def main() -> None:
    """Process pdf scans to separate assessment files"""
    logging.info(f'Arguments in ({len(sys.argv)}): {sys.argv}')

    for item in sys.argv[1:]:
        logging.info(f'Processing {item}:')
        cropcorner(item)
        ocrcorner(item)
        assessmentdict = buildpagelist2(item)
        processAssessment(item,assessmentdict)
        cleanup(item)
        logging.info('\t...done')
    
    return None

if __name__ == '__main__':
    sys.exit(main())
