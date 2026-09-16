import json
from collections import defaultdict
from classifier import classify_email
from disposition import assign_dispositions, print_statistics, save_dispositions_to_file

def main():
    # Load inbox
    with open('Docs/inbox.json', 'r') as f:
        emails = json.load(f)
    
    # Part 2: Assign dispositions to all emails
    print("\n" + "=" * 70)
    print("PART 2: ZEROING IT - Assigning Dispositions")
    print("=" * 70)
    
    results, stats = assign_dispositions(emails)
    
    # Verify every message has a disposition
    unassigned = [r for r in results if r["disposition"] is None]
    if unassigned:
        print(f"ERROR: {len(unassigned)} messages without disposition!")
        for r in unassigned:
            print(f"  {r['id']}: {r['subject']}")
        return
    
    print(f"✓ Verification passed: All {len(results)} messages have dispositions\n")
    
    # Print statistics
    print_statistics(results, stats)
    
    # Save to file
    save_dispositions_to_file(results)


if __name__ == '__main__':
    main()
