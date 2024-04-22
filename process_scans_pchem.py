import subprocess
import sys
import os
from pathlib import Path  # for sorting paths below (supercedes glob)
import logging
import re  # regular expressions
from string import Template  # used in annotations
from subprocess import CompletedProcess

import numpy as np
import yaml

# set up logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# path to gs >= 9.54
gs_cmd = '/Users/SGR/Downloads/ghostscript-9.55.0/bin/gs'

# path to tessdata files
TESSDATA_PREFIX = '/Users/SGR/Downloads/tessdata_fast-main/'

# environmental variable
my_env = os.environ.copy()
my_env["TESSDATA_PREFIX"] = TESSDATA_PREFIX

# assessment list
ASS_LIST = ['10a', '1c', '2c', '3c', '4c', '5c', '6c',
            '7c', '8c', '9b']


def crop_corner(pdf_in) -> CompletedProcess[bytes]:
    """Crop the corner of the pdf file to extract the assessment name"""
    logging.info(f'\t...cropping {pdf_in} to crop_{pdf_in}')
    # third try title
    size_str = '1700x750'
    offset_str = '-45 -675'
    
    x = subprocess.run([gs_cmd, '-q', '-o', 'crop_' + pdf_in, '-sDEVICE=pdfwrite', f'-g{size_str}', '-c', f'"<</PageOffset [{offset_str}]>> setpagedevice"', '-f', pdf_in])
    
    return x


def ocr_corner(pdf_in) -> CompletedProcess[bytes]:
    """run ocr on the cropped corner"""
    logging.info(f'\t...running OCR on crop_{pdf_in}')
    x = subprocess.run([gs_cmd, '-q', '-o', 'crop_' + pdf_in + '-%03d.txt', '--permit-file-read=$TESSDATA_PREFIX', '-sDEVICE=ocr', '-r600', '-dDownScaleFactor=3', 'crop_' + pdf_in], env=my_env)
    return x


def build_page_list3(pdf_in) -> dict:
    logging.info('\t...build list of assessments')

    batch_of_files = sorted(Path('.').glob(f'crop_{pdf_in}-*.txt'))
    n_pages_expected_per_student = len(ASS_LIST)
    n_pages_in_this_batch = len(batch_of_files)
    if n_pages_in_this_batch % n_pages_expected_per_student == 0:
        # if pages in batch is a multiple of the expected number
        assessment_page_dict = process_expected(batch_of_files)
    else:
        assessment_page_dict = process_unexpected(batch_of_files,
                                                  pdf_in=pdf_in)
        
    return assessment_page_dict


def process_expected(batch_of_files) -> dict:

    # (note int divide "//" )
    n_pages_expected_per_student = len(ASS_LIST)
    n_pages_in_this_batch = len(batch_of_files)
    n_students_guess = n_pages_in_this_batch//n_pages_expected_per_student
    logging.debug(f'\t... got the expected number of pages \
                      ({n_pages_in_this_batch}) for {n_students_guess} \
                      students')
    
    page_guess = [x + 1 + y * n_pages_expected_per_student
                  for y in range(n_students_guess) 
                  for x in range(n_pages_expected_per_student)]
    ass_guess = ASS_LIST * n_students_guess
    expected_dict = dict(zip(page_guess, ass_guess))
    
    page_ass_dict = build_page_assessment_dict(batch_of_files)
    
    # look for errors
    for key, val in page_ass_dict.items():
        if val is None:
            # we're guessing it is probably ok
            flag_ok_test1 = True
            flag_ok_test2 = True
            if key-1 in page_ass_dict:
                if page_ass_dict[key-1] != expected_dict[key-1]:
                    flag_ok_test1 = False
            if key+1 in page_ass_dict:
                if page_ass_dict[key+1] != expected_dict[key+1]:
                    flag_ok_test2 = False
            flag_ok = flag_ok_test1 and flag_ok_test2
            if flag_ok:
                logging.debug(f'Guessing that page {key} is assessment {expected_dict[key]}')
                page_ass_dict[key] = expected_dict[key]
            else:
                page_ass_dict[key] = get_assessment_from_user(key, expected_dict[key])
                
    logging.debug(page_ass_dict)
    flipped = flip_dictionary(page_ass_dict)
    logging.debug(flipped)

    return flipped


def build_page_assessment_dict(batch_of_files) -> dict:
    page_list = []
    ass_list = []
    for file in batch_of_files:
        m = re.search(r'(?<=pdf-)\d+(?=\.txt)', str(file))
        if m:
            page_number = int(m[0])
        else:
            raise ValueError(f'Unable to extract the page number from {file}')

        logging.debug(page_number)
        
        with open(file, 'r') as fid:
            ocr_text = fid.read()
        logging.debug(ocr_text)

        assessment_string = get_assessment_from_ocr(ocr_text)
        page_list.append(page_number)
        ass_list.append(assessment_string)
    # put them in a dictionary where pages are keys and assessments are values
    page_ass_dict = dict(zip(page_list, ass_list))
    return page_ass_dict


def get_assessment_from_user(page,
                             expected_assessment=None,
                             maybe_assessment=None,
                             hint=None,
                             pdf_in=None) -> str:
    if not hint:
        hint = ''

    if expected_assessment:
        print(f'Trouble on page {page}. Probably it is {expected_assessment}.')
        default_ans = expected_assessment
    elif maybe_assessment:
        print(f'Trouble on page {page}. {hint} Maybe it is {maybe_assessment}.')
        default_ans = maybe_assessment
    else:
        default_ans = []
        print(f'Trouble on page {page}. No guess.')

    # open pdf to help user
    open_pdf_at_page(pdf_in, page)

    assessment_string = []
    while not assessment_string:
        prompt = f'What is the assessment number [{default_ans}]:\n'
        val = input(prompt).strip() or default_ans
        if val in ASS_LIST:
            assessment_string = val
        else:
            print(f'{val} is not in the assessment list. Try again.')
    
    return assessment_string


def get_assessment_from_ocr(ocr_text) -> str:
    # search for assessment by "Assessment 3.2a" template
    # seem to get a lot of extra .'s or \'s and 1 often reads as l
    # m as n, extra ` or ', e as a, . as :
    pattern = r'(?<=[mn][eaé]nt )[\dlIi]+[a-z]'
    m = re.search(pattern, ocr_text)
    if not m:
        # see if there is an extra . \ ' ` , 
        pattern = r"(?<=[mn][eaé]nt [\.\\\'\`,])[\dlIi]+[a-z]"
        m = re.search(pattern, ocr_text)
    if not m:
        # see if they are before the space
        pattern = r"(?<=[mn][eaé]nt[\.\\\'\`,] )[\dlIi]+[a-z]"
        m = re.search(pattern, ocr_text)
    if m:    
        # hopefully we found something
        ass_number = m[0].replace('l', '1').replace('L', '1').replace('i', '1').replace('I', '1')
    else:
        # if not
        ass_number = m  # None if still no match
    
    return ass_number


def process_unexpected(batch_of_files, pdf_in) -> dict:
    
    n_pages_expected_per_student = len(ASS_LIST)
    n_pages_in_this_batch = len(batch_of_files)
    n_students_guess = n_pages_in_this_batch // n_pages_expected_per_student
    remainder = n_pages_in_this_batch % n_pages_expected_per_student
    logging.warning(('\t... did NOT get the expected number of pages. \n',
                     f'Got ({n_pages_in_this_batch}) for {n_students_guess}',
                     f'students with {remainder} left over'))

    page_ass_dict = build_page_assessment_dict(batch_of_files)
    
    # look for errors
    for key, val in page_ass_dict.items():
        if val is not None:
            continue

        prev_ass_idx = np.nan  # invalid values
        next_ass_idx = np.nan
        if key - 1 in page_ass_dict:
            prev_ass_idx = ASS_LIST.index(page_ass_dict[key - 1])
        if key + 1 in page_ass_dict:
            next_ass_idx = ASS_LIST.index(page_ass_dict[key + 1])

        # calculate how far away the indices are using mod to wrap around
        diff = (next_ass_idx - prev_ass_idx) % len(ASS_LIST)
        if diff == 2:
            # it looks like a scratch out (between prev and next)
            maybe = ASS_LIST[prev_ass_idx + 1]
            hint = 'It looks like a scratch out.'
        elif diff == 1:
            # it looks like an extra page (same as prev)
            maybe = ASS_LIST[prev_ass_idx]
            hint = 'It looks like an extra page.'
        else:
            maybe = None
            hint = 'No guess.'

        page_ass_dict[key] = (
            get_assessment_from_user(key,
                                     maybe_assessment=maybe,
                                     hint=hint,
                                     pdf_in=pdf_in))

    logging.debug(page_ass_dict)
    flipped = flip_dictionary(page_ass_dict)
    logging.debug(flipped)

    return flipped

    
def flip_dictionary(d) -> dict:
    flipped = {}
    for key, value in d.items():
        if value not in flipped:
            flipped[value] = [key]
        else:
            flipped[value].append(key)
    return flipped


def process_assessment(pdf_in, assessment_dict) -> (
        CompletedProcess[bytes] | None):
    logging.info('\t...extracting pages')
    x = None
    for key in assessment_dict:
        ass_name = 'A' + key + '_' + pdf_in
        logging.debug(ass_name)
        value = assessment_dict[key]
        # must be in increasing order so sort, then make strings,
        # then combine with comma sep
        value.sort()  # sorts in place
        tmp = [str(num) for num in value]
        page_list = ','.join(tmp)
        logging.debug('Page list = ' + page_list)
        logging.debug(' '.join([gs_cmd, '-q', '-o', ass_name, '-sPageList=' + page_list, '-sDEVICE=pdfwrite', pdf_in]))
        x = subprocess.run([gs_cmd, '-q', '-o', ass_name, '-sPageList=' + page_list, '-sDEVICE=pdfwrite', pdf_in])
        x.check_returncode()

        x = add_annotations_to_pdf(pdf_in, ass_name, key, value)
        x.check_returncode()
    return x


def add_annotations_to_pdf(pdf_in, file_name_in, assessment_name,
                           original_page_list) -> CompletedProcess[bytes]:

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
    d = {'pdfin': pdf_in, 'assessment_name': assessment_name}
    count = 0
    with open(pdfmarks_file_name, "w") as pdfmarks_file:
        for orig_page in original_page_list:
            count += 1
            d['this_page'] = count
            d['original_page'] = orig_page
            pdfmarks_file.write(Template(template_string).safe_substitute(d))
            
    x = subprocess.run([gs_cmd, '-dBATCH', '-dNOPAUSE', '-dQUIET',
                        '-sDEVICE=pdfwrite', f'-sOutputFile={file_name_out}',
                        pdfmarks_file_name, file_name_in])
    
    return x


def cleanup(pdf_in):
    logging.info('\t...cleaning up')

    dir_dict = {
        'originals': Path('./originals'),
        'cropped': Path('./cropped'),
        'ocrtxt': Path('./ocrtxt'),
        'split': Path('./split')
    }

    for p in dir_dict.values():
        if p.is_dir():
            logging.debug(f'\t...found dir {p}')
        else:
            logging.debug(f'\t...making dir {p}')
            p.mkdir()
            
    # remove all temp files
    for file in sorted(Path('.').glob(f'crop_{pdf_in}-*.txt')):
        destination = dir_dict['ocrtxt'] / file
        file.replace(destination)
    for file in sorted(Path('.').glob(f'A*_{pdf_in}')):
        destination = dir_dict['split'] / file
        file.replace(destination)

    # move processed pdf to originals directory
    source = Path(pdf_in)
    destination = dir_dict['originals'] / pdf_in
    source.replace(destination)

    # move cropped pages to processed directory
    for file in sorted(Path('.').glob(f'crop_{pdf_in}')):
        destination = dir_dict['cropped'] / file
        file.replace(destination)


def summarize(pdf_in):
    # https://stackoverflow.com/questions/4826485/ghostscript-pdf-total-pages

    module_path = Path(__file__).parent
    cmd = module_path / 'summarize.sh'
    if cmd.exists():
        logging.debug(f'found summarize.sh at {cmd}')
    x = subprocess.run([cmd, len(ASS_LIST), pdf_in], stdout=subprocess.PIPE)
    logging.info(x.stdout.decode('utf-8'))
    return x    
    

def open_pdf_at_page(pdf_name: Path | str, page: int) -> None:
    """
    Open pdf at given page number.

    :param pdf_name: name of pdf file
    :type pdf_name: pathlib.Path | str
    :param page: the page to open
    :type page: int
    :returns: None
    """

    module_path = Path(__file__).parent
    scripty = module_path / 'open_pdf_to_page.scpt'
    pdf_full_path = Path(pdf_name)
    x = subprocess.run(['osascript',
                        scripty.resolve(),
                        pdf_full_path.resolve(),
                        f'{int(page)}'])
    x.check_returncode()

    return


def main(this_item) -> None:
            
    logging.info(f'Processing {this_item}:')
    summarize(this_item)
    crop_corner(this_item)
    ocr_corner(this_item)
    assessment_dict = build_page_list3(this_item)
    process_assessment(this_item, assessment_dict)
    cleanup(this_item)
    logging.info('\t...done')
    
    return None


if __name__ == '__main__':
    """Process pdf scans to separate assessment files"""
    logging.info(f'Arguments in ({len(sys.argv)}): {sys.argv}')

    config_file_name = 'assessments.yaml'
    config_file_path = Path(config_file_name)
    if config_file_path.exists():
        logging.debug(f'Found config file ({config_file_name})...')
        with open(config_file_path, 'r') as stream:
            yaml_content = yaml.load(stream, Loader=yaml.CLoader)
        ASS_LIST = yaml_content['assessments']
    else:
        logging.debug(f'Found no config file, using defaults...')

    logging.info(f'... assessment list ({ASS_LIST})')

    for item in sys.argv[1:]:
        if not os.path.exists(item):
            raise FileNotFoundError(f'Cannot locate file {item}.')
        main(item)
    sys.exit()
