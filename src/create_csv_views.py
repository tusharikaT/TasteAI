import os
import csv

# Increase field size limit for reading the original file
csv.field_size_limit(10 * 1024 * 1024)

DATA_DIR = r"c:\Users\DELL\zomato-milestone\data"
INPUT_CSV = os.path.join(DATA_DIR, "zomato.csv")
COMPACT_CSV = os.path.join(DATA_DIR, "zomato_compact.csv")
PREVIEW_CSV = os.path.join(DATA_DIR, "zomato_preview.csv")

def create_views():
    if not os.path.exists(INPUT_CSV):
        print(f"Error: Original CSV file not found at {INPUT_CSV}")
        return

    print("Reading original CSV and generating simplified views...")
    
    with open(INPUT_CSV, "r", encoding="utf-8-sig", errors="replace") as infile:
        reader = csv.reader(infile)
        
        # Read header
        try:
            header = next(reader)
        except StopIteration:
            print("Error: CSV file is empty.")
            return
            
        # Identify indexes of large columns
        try:
            reviews_idx = header.index("reviews_list")
        except ValueError:
            reviews_idx = -1
            
        try:
            menu_idx = header.index("menu_item")
        except ValueError:
            menu_idx = -1
            
        # Create header for compact CSV
        compact_header = [h for i, h in enumerate(header) if i not in (reviews_idx, menu_idx)]
        
        print(f"Compact columns: {compact_header}")
        
        # Open output files
        with open(COMPACT_CSV, "w", newline="", encoding="utf-8") as comp_file, \
             open(PREVIEW_CSV, "w", newline="", encoding="utf-8") as prev_file:
             
            comp_writer = csv.writer(comp_file)
            prev_writer = csv.writer(prev_file)
            
            comp_writer.writerow(compact_header)
            prev_writer.writerow(header)
            
            row_count = 0
            compact_written = 0
            preview_written = 0
            
            for row in reader:
                row_count += 1
                
                # Write to compact file (drop the large columns)
                compact_row = [val for i, val in enumerate(row) if i not in (reviews_idx, menu_idx)]
                comp_writer.writerow(compact_row)
                compact_written += 1
                
                # Write to preview file (first 500 rows only, keep all columns)
                if row_count <= 500:
                    prev_writer.writerow(row)
                    preview_written += 1
                    
                if row_count % 10000 == 0:
                    print(f"Processed {row_count} rows...")
                    
    print(f"Finished! Processed {row_count} total rows.")
    print(f"Created compact file: {COMPACT_CSV} ({compact_written} rows, dropped 'reviews_list' and 'menu_item').")
    print(f"Created preview file: {PREVIEW_CSV} ({preview_written} rows, first 500 rows with all columns).")

if __name__ == "__main__":
    create_views()
