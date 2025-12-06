import sys
import os
os.chdir('spdf-server')
sys.path.insert(0, 'spdf-server')

from models import generate_license_key

# Generate key for user 1 and DOC-E2E-001
key = generate_license_key()
print(f"\n🔑 LICENSE KEY: {key}\n")
print("Use this key in the viewer to open the SPDF file!")
