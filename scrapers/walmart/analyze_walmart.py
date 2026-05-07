import sys
import os
# pyrefly: ignore [missing-import]
from bs4 import BeautifulSoup

def analyze_html(file_path):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        html = f.read()

    soup = BeautifulSoup(html, 'html.parser')
    
    print("--- Analyzing Selectors ---")
    
    # Check item containers
    stacks = soup.select('[data-testid="item-stack"]')
    print(f"Found {len(stacks)} item-stacks")
    for i, stack in enumerate(stacks):
        children = stack.find_all(recursive=False)
        print(f"Stack {i} has {len(children)} direct children")
        if children:
            child = children[0]
            print(f"First child tag: {child.name}, classes: {child.get('class')}")
    
    # Check for titles
    titles = soup.select('[data-automation-id="product-title"]')
    print(f"Found {len(titles)} data-automation-id='product-title'")
    
    titles_test = soup.select('[data-testid="product-title"]')
    print(f"Found {len(titles_test)} data-testid='product-title'")
    
    # If no titles found, search for anything with "title" in class or attribute
    if not titles and not titles_test:
        print("Searching for anything with 'title'...")
        potential = soup.find_all(lambda tag: tag.get('data-automation-id') and 'title' in tag.get('data-automation-id').lower())
        for p in potential[:5]:
            print(f"Potential title attribute: {p.get('data-automation-id')} (Tag: {p.name})")
            
        potential_class = soup.find_all(lambda tag: tag.get('class') and any('title' in c.lower() for c in tag.get('class')))
        for p in potential_class[:5]:
            print(f"Potential title class: {p.get('class')} (Tag: {p.name})")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        analyze_html(sys.argv[1])
    else:
        print("Usage: python analyze_walmart.py <html_file>")
