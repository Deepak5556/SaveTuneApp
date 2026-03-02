import zipfile
import xml.etree.ElementTree as ET
import sys

def extract_text_from_docx(docx_path):
    try:
        with zipfile.ZipFile(docx_path, 'r') as docx:
            xml_content = docx.read('word/document.xml')
            tree = ET.fromstring(xml_content)
            
            # The namespace for WordprocessingML
            ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            
            # Find all text nodes
            text_nodes = tree.findall('.//w:t', ns)
            text = '\n'.join([node.text for node in text_nodes if node.text])
            return text
    except Exception as e:
        return str(e)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        text = extract_text_from_docx(sys.argv[1])
        with open("blueprint.txt", "w", encoding="utf-8") as f:
            f.write(text)
        print("Extracted to blueprint.txt")
    else:
        print("Provide docx path")
