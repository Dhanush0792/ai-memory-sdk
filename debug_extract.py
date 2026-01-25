"""Debug test - trace extract execution"""
import sys
sys.path.insert(0, 'c:/Users/Desktop/Projects/memory')

from api.services.memory_extractor import MemoryExtractor

print("Testing MemoryExtractor directly...")
print("="*60)

try:
    extractor = MemoryExtractor()
    print("✓ Extractor created")
    
    print("\nCalling extract('My name is Alice')...")
    result = extractor.extract("My name is Alice")
    
    print(f"Result type: {type(result)}")
    print(f"Result: {result}")
    print(f"Length: {len(result)}")
    
    if len(result) == 0:
        print("\n❌ PROBLEM: Returned empty array without error!")
    else:
        print("\n✓ Got results")
        
except ValueError as e:
    print(f"\n✓ ValueError raised (expected): {e}")
except Exception as e:
    print(f"\n✓ Exception raised: {type(e).__name__}: {e}")
