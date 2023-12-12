import subprocess
import sys
import os
#import glob
from pathlib import Path #for sorting paths below (supercedes glob)
import logging
import re #regular expressions (needed searching for bond angles in chemFigString)
from string import Template #used in annotations

#set up logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
#logger.setLevel(logging.INFO)

# path to gs >= 9.54
gscmd = '/Users/SGR/Downloads/ghostscript-9.55.0/bin/gs'

# path to tessdata files
TESSDATA_PREFIX = '/Users/SGR/Downloads/tessdata_fast-main/'

# environmental variable
my_env = os.environ.copy()
my_env["TESSDATA_PREFIX"] = TESSDATA_PREFIX

# assessment list
ASSLIST = ['5.1', '1.1','1.2','1.3','2.1','2.2','2.3','2.3','3.1','3.2','3.3','4.1','4.2','4.2','4.3']

def cropcorner(pdfin) -> int:
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
    
    return x

def ocrcorner(pdfin) -> int:
    """run ocr on the cropped corner"""
    logging.info(f'\t...running OCR on crop_{pdfin}')
    x = subprocess.run([gscmd,'-q','-o','crop_'+pdfin+'-%03d.txt','--permit-file-read=$TESSDATA_PREFIX','-sDEVICE=ocr','-r600','-dDownScaleFactor=3','crop_'+pdfin],env=my_env)
    return x

def buildpagelist2(pdfin):
    logging.info('\t...build list of assessments')

    pageassdict = {}
    #oldassnumber = '5.1' #first page
    #oldpagenumber = 0

    for file in sorted(Path('.').glob(f'crop_{pdfin}-*.txt')):
        #m = re.search(r'.*pdf-(\d+).txt',file)
        pagenumber = re.findall(r'(?<=pdf-)\d+(?=\.txt)',str(file))
        logging.debug(pagenumber)
        
        with open(file,'r') as fid:
            ocrtext = fid.read()
        logging.debug(ocrtext)
        ## search for assessment by A3.2v template
        ##m = re.search(r'A(\d.\d)v',file)
        #assnumber = re.findall(r'\d\.\d(?=[abc]v\d+)',ocrtext)

        # search for assessment by "Assessment 3.2a" template
        # seem to get a lot of extra .'s or \'s and 1 often reads as l
        # m as n, extra ` or ', e as a, . as :
        assnumber = re.findall(r'(?<=ment )\d\.[\dl]',ocrtext)
        if not assnumber:
            assnumber = re.findall(r'(?<=ment \\)\d\.[\dl]',ocrtext)
        if not assnumber:
            assnumber = re.findall(r'(?<=ment. )\d\.[\dl]',ocrtext)

        if not assnumber:
            assnumber = [ASSLIST[(int(pagenumber[0])-1)%len(ASSLIST)]]
            logging.warning('GUESSING ' + str(pagenumber) +' is ' + str(assnumber))
        if assnumber:
            #logging.warning(print(assnumber))
            if assnumber[-1][-1]=='l':
                assnumber[-1] = assnumber[-1][:-1] + '1'

            logging.info(f'\t...page {pagenumber} assessment {assnumber}')
            pageassdict[int(pagenumber[0])]=assnumber[0]
            #oldassnumber = assnumber[0]
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

def buildpagelist3(pdfin)->dict:
    logging.info('\t...build list of assessments')

    #oldassnumber = '5.1' #first page
    #oldpagenumber = 0
    batch_of_files = sorted(Path('.').glob(f'crop_{pdfin}-*.txt'))
    n_pages_expected_per_student = len(ASSLIST)
    n_pages_in_this_batch = len(batch_of_files)
    if n_pages_in_this_batch % n_pages_expected_per_student == 0:
        # if pages in batch is a multiple of the expected number
        assessment_page_dict = process_expected(batch_of_files)
    else:
        assessment_page_dict = process_unexpected(batch_of_files)
        
    return assessment_page_dict

def process_expected(batch_of_files)->dict:

    # (note int divide "//" )
    n_pages_expected_per_student = len(ASSLIST)
    n_pages_in_this_batch = len(batch_of_files)
    n_students_guess = n_pages_in_this_batch//n_pages_expected_per_student
    logging.debug(f'\t... got the expected number of pages \
                      ({n_pages_in_this_batch}) for {n_students_guess} \
                      students')
    
    page_guess = [x + 1 + y * n_pages_expected_per_student
                  for y in range(n_students_guess) 
                  for x in range(n_pages_expected_per_student)]
    ass_guess = ASSLIST * n_students_guess
    expected_dict = dict(zip(page_guess,ass_guess))
    
    pageassdict = build_page_assessment_dict(batch_of_files)
    
    #look for errors
    for key, val in pageassdict.items():
        if val is None:
            # we're guessing it is probably ok
            flag_ok_test1 = True
            flag_ok_test2 = True
            if key-1 in pageassdict:
                if pageassdict[key-1] != expected_dict[key-1]:
                    flag_ok_test1 = False
            if key+1 in pageassdict:
                if pageassdict[key+1] != expected_dict[key+1]:
                    flag_ok_test2 = False
            flag_ok = flag_ok_test1 and flag_ok_test2
            if flag_ok:
                logging.debug(f'Guessing that page {key} is assessment {expected_dict[key]}')
                pageassdict[key] = expected_dict[key]
            else:
                pageassdict[key] = get_assessment_from_user(key,expected_dict[key])
                
    logging.debug(pageassdict)
    flipped = flip_dictionary(pageassdict)
    logging.debug(flipped)

    return flipped

def build_page_assessment_dict(batch_of_files)->dict:
    page_list = []
    ass_list = []
    for file in batch_of_files:
        m = re.search(r'(?<=pdf-)\d+(?=\.txt)',str(file))
        if m:
            pagenumber = int(m[0])
        else:
            raise ValueError(f'Unable to extract the page number from {file}')

        logging.debug(pagenumber)
        
        with open(file,'r') as fid:
            ocrtext = fid.read()
        logging.debug(ocrtext)

        assessment_string = get_assessment_from_ocr(ocrtext)            
        page_list.append(pagenumber)
        ass_list.append(assessment_string)
    #put them in a dictionary where pages are keys and assessments are values
    pageassdict = dict(zip(page_list,ass_list))
    return pageassdict

def get_assessment_from_user(page,expected_assessment=[])->str:
    print(f'Trouble on page {page}. Expected {expected_assessment}.')
    assessment_string = []
    while assessment_string == []:
        #val = input('What is the assessment for:\n' + ocrtext +'\n:\n') 
        val = input('What is the assessment number:\n') 
        if val in ASSLIST:
            assessment_string = val
        else:
            print(f'{val} is not in the assessment list. Try again.')
    
    return assessment_string

def get_assessment_from_ocr(ocrtext)->str:
    # search for assessment by "Assessment 3.2a" template
    # seem to get a lot of extra .'s or \'s and 1 often reads as l
    # m as n, extra ` or ', e as a, . as :
    pattern = r'(?<=[mn][eaé]nt )[\dl][\.:][\dl]'
    m = re.search(pattern,ocrtext)
    if not m:
        # see if there is an extra . \ ' ` , 
        pattern = r"(?<=[mn][eaé]nt [\.\\\'\`,])[\dl][\.:][\dl]"
        m = re.search(pattern,ocrtext)
    if not m:
        # see if they are before the space
        pattern = r"(?<=[mn][eaé]nt[\.\\\'\`,] )[\dl][\.:][\dl]"
        m = re.search(pattern,ocrtext)
    if m:    
        # hopefully we found something
        assnumber = m[0].replace('l','1').replace(':','.')
    else:
        # if not
        assnumber = m #None if still no match
    
    return assnumber


def process_unexpected(batch_of_files)->dict:
    
    n_pages_expected_per_student = len(ASSLIST)
    n_pages_in_this_batch = len(batch_of_files)
    n_students_guess = n_pages_in_this_batch // n_pages_expected_per_student
    remainder = n_pages_in_this_batch % n_pages_expected_per_student
    logging.warning(['\t... did NOT get the expected number of pages. \n',
                     f'Got ({n_pages_in_this_batch}) for {n_students_guess}',
                     f'students with {remainder} left over'])

    pageassdict = build_page_assessment_dict(batch_of_files)
    
    #look for errors
    for key, val in pageassdict.items():
        if val is None:
            pageassdict[key] = get_assessment_from_user(key)

    logging.debug(pageassdict)
    flipped = flip_dictionary(pageassdict)
    logging.debug(flipped)

    return flipped

    
def flip_dictionary(d)->dict:
    flipped = {}
    for key, value in d.items():
        if value not in flipped:
            flipped[value] = [key]
        else:
            flipped[value].append(key)
    return flipped

def processAssessment(pdfin,assessmentdict)->int:
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
        
        x = add_annotations_to_pdf(pdfin,assName,key,value)

    return x

def add_annotations_to_pdf(pdfin,file_name_in,assessment_name,original_page_list)->int:

    pdfmarks_file_name = 'pdfmarks.txt'
    template_string = r'''[
/Subtype /FreeText
/SrcPg $this_page
/Rect [0 0 144 24]
/Color [1 1 1]
/DA (/HeBo 8 Tf 0 0 0 rg)
/Contents ($pdfin p.${original_page} -> A${assessment_name})
/ANN pdfmark

'''    
    file_name_out = file_name_in.rstrip('.pdf') + '_annotated' + '.pdf'
    d = {'pdfin':pdfin,'assessment_name':assessment_name}
    count = 0
    with open(pdfmarks_file_name,"w") as pdfmarks_file:
        for orig_page in original_page_list:
            count += 1
            d['this_page'] = count
            d['original_page'] = orig_page
            pdfmarks_file.write(Template(template_string).safe_substitute(d))
            
        #gs -dBATCH -dNOPAUSE -dQUIET -sDEVICE=pdfwrite -sOutputFile=annotated.pdf  pdfmarks.txt original.pdf
    x = subprocess.run([gscmd,'-dBATCH','-dNOPAUSE','-dQUIET', 
                        '-sDEVICE=pdfwrite',f'-sOutputFile={file_name_out}',
                        pdfmarks_file_name, file_name_in])
    
    return x


def cleanup(pdfin):
    logging.info('\t...cleaning up')

    dirdict = {}
    dirdict['originals'] =  Path('./originals')
    #dirdict['processed'] =  Path('./processed')
    dirdict['cropped'] =  Path('./cropped')
    dirdict['ocrtxt'] = Path('./ocrtxt')
    dirdict['split'] = Path('./split')

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
    for file in sorted(Path('.').glob(f'A*_{pdfin}')):
        #file.unlink() 
        destination = dirdict['split'] / file
        file.replace(destination)
        
    
    # move processed pdf to originals directory
    source = Path(pdfin)
    destination = dirdict['originals'] / pdfin
    source.replace(destination)

    #move cropped pages to processed directory
    for file in sorted(Path('.').glob(f'crop_{pdfin}')):
        destination = dirdict['cropped'] / file
        file.replace(destination)

def summarize(pdfin):
    #https://stackoverflow.com/questions/4826485/ghostscript-pdf-total-pages
    x = subprocess.run(['./summarize.sh',pdfin],stdout=subprocess.PIPE)
    logging.info(x.stdout.decode('utf-8'))
    return x    
    

def main() -> None:
    """Process pdf scans to separate assessment files"""
    logging.info(f'Arguments in ({len(sys.argv)}): {sys.argv}')

    for item in sys.argv[1:]:
        if not os.path.exists(item):
            raise FileNotFoundError(f'Cannot locate file {item}.')
            
        logging.info(f'Processing {item}:')
        summarize(item)
        cropcorner(item)
        ocrcorner(item)
        assessmentdict = buildpagelist3(item)
        processAssessment(item,assessmentdict)
        cleanup(item)
        logging.info('\t...done')
    
    return None

if __name__ == '__main__':
    sys.exit(main())
