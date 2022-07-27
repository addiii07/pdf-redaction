# Import Libraries
from typing import Tuple
from io import BytesIO
import os
import argparse
import re
import fitz


def extract_info(input_file: str):
    """
    Extracts file info
    """
    # Open the PDF
    pdfDoc = fitz.open(input_file)
    output = {
        "File": input_file, "Encrypted": ("True" if pdfDoc.isEncrypted else "False")
    }
    
    if not pdfDoc.isEncrypted:
        for key, value in pdfDoc.metadata.items():
            output[key] = value

    print("## File Information ##################################################")
    print("\n".join("{}:{}".format(i, j) for i, j in output.items()))
    print("######################################################################")

    return True, output


def search_for_text(lines, search_str):
    """
    Search for the search string within the document lines
    """
    for line in lines:
        results = re.findall(search_str, line, re.IGNORECASE)
        # for multiple matches in a line
        for result in results:
            yield result


def redact_matching_data(page, matched_values):
    """
    Redacts matching values
    """
    matches_found = 0
    for val in matched_values:
        matches_found += 1
        
        matching_val_area = page.search_for(val)
        # Redacting matching values
        [page.add_redact_annot(area, text=" ", fill=(0, 0, 0))
         for area in matching_val_area]
    # To apply the redaction
    page.apply_redactions()
    return matches_found



def process_data(input_file: str, output_file: str, search_str: str, pages: Tuple = None, action: str = 'Highlight'):
    """
    Process the pages of the PDF File
    """
    pdfDoc = fitz.open(input_file)
    output_buffer = BytesIO()
    total_matches = 0
    # Iterate through pages
    for pg in range(pdfDoc.page_count):
        if pages:
            if str(pg) not in pages:
                continue
        page = pdfDoc[pg]
        page_lines = page.get_text("text").split('\n')
        matched_values = search_for_text(page_lines, search_str)
        if matched_values:
            if action == 'Redact':
                matches_found = redact_matching_data(page, matched_values)
            total_matches += matches_found
    print(f"{total_matches} Match(es) Found of Search String {search_str} In Input File: {input_file}")
    pdfDoc.save(output_buffer)
    pdfDoc.close()
    # Save the output buffer to the output file
    with open(output_file, mode='wb') as f:
        f.write(output_buffer.getbuffer())


def process_file(**kwargs):
    """
    To process one single file
    """
    input_file = kwargs.get('input_file')
    output_file = kwargs.get('output_file')
    if output_file is None:
        output_file = input_file
    search_str = kwargs.get('search_str')
    pages = kwargs.get('pages')
    # To Redact
    action = kwargs.get('action')
    if action == "Remove":
            print("")
    else:
        process_data(input_file=input_file, output_file=output_file,
                     search_str=search_str, pages=pages, action=action)


def process_folder(**kwargs):
    """
    Redact all PDF Files within a specified path
    """
    input_folder = kwargs.get('input_folder')
    search_str = kwargs.get('search_str')
    recursive = kwargs.get('recursive')
    action = kwargs.get('action')
    pages = kwargs.get('pages')
    for foldername, dirs, filenames in os.walk(input_folder):
        for filename in filenames:
            # Check if pdf file
            if not filename.endswith('.pdf'):
                continue
             # PDF File found
            inp_pdf_file = os.path.join(foldername, filename)
            print("Processing file =", inp_pdf_file)
            process_file(input_file=inp_pdf_file, output_file=None,
                         search_str=search_str, action=action, pages=pages)
        if not recursive:
            break


def is_valid_path(path):
    """
    Validates the path inputted and checks whether it is a file path or a folder path
    """
    if not path:
        raise ValueError(f"Invalid Path")
    if os.path.isfile(path):
        return path
    elif os.path.isdir(path):
        return path
    else:
        raise ValueError(f"Invalid Path {path}")


def parse_args():
    """
    Get user command line parameters
    """
    parser = argparse.ArgumentParser(description="Available Options")
    parser.add_argument('-i', '--input_path', dest='input_path', type=is_valid_path,
                        required=True, help="Enter the path of the file or the folder to process")
    parser.add_argument('-a', '--action', dest='action', choices=['Redact'], type=str,
                        default='Highlight', help="Choose to Redact ")
    parser.add_argument('-p', '--pages', dest='pages', type=tuple,
                        help="Enter the pages to consider e.g.: [2,4]")
    action = parser.parse_known_args()[0].action
    if action != 'Remove':
        parser.add_argument('-s', '--search_str', dest='search_str'                            
                            , type=str, required=True, help="Enter a valid search string")
    path = parser.parse_known_args()[0].input_path
    if os.path.isfile(path):
        parser.add_argument('-o', '--output_file', dest='output_file', type=str  
                            , help="Enter a valid output file")
    if os.path.isdir(path):
        parser.add_argument('-r', '--recursive', dest='recursive', default=False, type=lambda x: (
            str(x).lower() in ['true', '1', 'yes']), help="Process Recursively or Non-Recursively")
    args = vars(parser.parse_args())
    # To Display The Command Line Arguments
    print("## Command Arguments #################################################")
    print("\n".join("{}:{}".format(i, j) for i, j in args.items()))
    print("######################################################################")
    return args


if __name__ == '__main__':
    args = parse_args()
    if os.path.isfile(args['input_path']):
        extract_info(input_file=args['input_path'])
        # To Process a file
        process_file(
            input_file=args['input_path'], output_file=args['output_file'], 
            search_str=args['search_str'] if 'search_str' in (args.keys()) else None, 
            pages=args['pages'], action=args['action']
        )
    # If its a Folder Path
    elif os.path.isdir(args['input_path']):
        process_folder(
            input_folder=args['input_path'], 
            search_str=args['search_str'] if 'search_str' in (args.keys()) else None, 
            action=args['action'], pages=args['pages'], recursive=args['recursive']
        )