import os
import re
def delete_keys_and_firmware(emulator):
    yuzu_dest = os.path.join(os.getenv('APPDATA'), 'Yuzu')
    ryujinx_dest = os.path.join(os.getenv('APPDATA'), 'Ryujinx')
    if emulator=="yuzu":
        os.remove(os.path.join(yuzu_dest, 'keys', 'prod.keys'))
        for root, dirs, files in os.walk(os.path.join(yuzu_dest, 'nand', 'system', 'Contents', 'registered')):
            for file in files:
                os.remove(os.path.join(root, file))
    elif emulator=="ryujinx":
        os.remove(os.path.join(ryujinx_dest, 'system', 'prod.keys'))
        for root, dirs, files in os.walk(os.path.join(ryujinx_dest, 'bis', 'system', 'Contents', 'registered')):
            for file in files:
                os.remove(os.path.join(root, file))
def display_available_versions():
    print("\nAvailable versions:")
    versions_available=[]
    folders = [f.name for f in os.scandir('.') if f.is_dir() and f.name != os.path.basename(__file__)] 
    for folder in folders:
        if re.match(r"\d+\.\d+\.\d+", str(folder)):
            versions_available.append(folder)
            print(folder)
    return versions_available
while True:
    emulator = input("Enter the emulator (Yuzu, Ryujinx, or Both): ")
    emulator = emulator.lower()
    if emulator in ['yuzu', 'ryujinx', 'both']:
        break
    print("Invalid emulator specified.")

versions=display_available_versions()

while True:
    version = input("Enter the version number (available versions are shown above): ").strip()
    if version in versions:
        break
    print("Invalid version number")

if emulator == "both":
    yuzu_dest = os.path.join(os.getenv('APPDATA'), 'Yuzu')
    ryujinx_dest = os.path.join(os.getenv('APPDATA'), 'Ryujinx')
    print("\nDeleting old keys and firmware for Yuzu...")
    delete_keys_and_firmware("yuzu")
    
    print("\nDeleting old keys and firmware for Ryujinx...")
    delete_keys_and_firmware("ryujinx")
  
    print("\nCopying files for Yuzu...")
    os.system(f'xcopy "{version}\\Yuzu" "{yuzu_dest}" /S /E /I /Y /Q')
    print("\nCopying files for Ryujinx...")
    os.system(f'xcopy "{version}\\Ryujinx" "{ryujinx_dest}" /S /E /I /Y /Q')
elif emulator == "yuzu":
    
    if emulator == "yuzu":
        dest = os.path.join(os.getenv('APPDATA'), 'Yuzu')
    else:
        dest = os.path.join(os.getenv('APPDATA'), 'Ryujinx')
    print("\nDeleting old keys and firmware...")
    os.remove(os.path.join(dest, 'keys', 'prod.keys'))
    for root, dirs, files in os.walk(os.path.join(dest, 'nand', 'system', 'Contents', 'registered')):
        for file in files:
            os.remove(os.path.join(root, file))
    print(f"\nCopying files for {emulator}...")
    os.system(f'xcopy "{version}\\{emulator}" "{dest}" /S /E /I /Y /Q')

input("\nPress Enter to exit.")