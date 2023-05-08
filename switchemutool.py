import io
import os
import re
import shutil
import threading
import time
import tkinter as tk
import zipfile
from tkinter import filedialog, messagebox
from urllib.parse import unquote
import base64
import customtkinter
import requests
from bs4 import BeautifulSoup


class DownloadStatusFrame(customtkinter.CTkFrame):
    def __init__(self, parent, filename):
        super().__init__(parent)
        self.grid_columnconfigure(0, weight=1)
        self.cancel_download_raised = False
        self.parent = parent
        self.filename = filename
        self.start_time = time.perf_counter()
        self.total_size = 0
        self.time_during_cancel = 0
        self.download_name = customtkinter.CTkLabel(self, text=filename)
        self.download_name.grid(row=0, column=0, sticky="W", padx=10, pady=5)

        self.progress_label = customtkinter.CTkLabel(self, text="0 MB / 0 MB")
        self.progress_label.grid(row=1, column=0, sticky="W", padx=10)

        self.progress_bar = customtkinter.CTkProgressBar(self, orientation="horizontal", mode="determinate")
        self.progress_bar.grid(row=2, column=0, columnspan=6, padx=(10,45), pady=5, sticky="EW")
        self.progress_bar.set(0)

        self.percentage_complete = customtkinter.CTkLabel(self, text="0%")
        self.percentage_complete.grid(row=2, column=5, sticky="E", padx=10)

        self.download_speed_label = customtkinter.CTkLabel(self, text="0 MB/s")
        self.download_speed_label.grid(row=1, column=5, sticky="E", padx=10)

        self.install_status_label = customtkinter.CTkLabel(self, text="Status: Downloading...")
        self.install_status_label.grid(row=3, column=0, sticky="W", padx=10, pady=5)

        self.eta_label = customtkinter.CTkLabel(self, text="ETA: 00:00:00")
        self.eta_label.grid(row=0, column=5, sticky="E", pady=5, padx=10)

        self.cancel_download_button = customtkinter.CTkButton(self, text="Cancel", command=self.cancel_button_event)
        self.cancel_download_button.grid(row=3, column=5, pady=10, padx=10, sticky="E")

    def update_download_progress(self, downloaded_bytes, chunk_size):
        
        done = downloaded_bytes / self.total_size
        avg_speed = downloaded_bytes / ((time.perf_counter() - self.start_time) - self.time_during_cancel)
        #cur_speed = chunk_size / (time.perf_counter() - self.time_at_start_of_chunk)
        time_left = (self.total_size - downloaded_bytes) / avg_speed

        minutes, seconds = divmod(int(time_left), 60)
        hours, minutes = divmod(minutes, 60)
        time_left_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        self.progress_bar.set(done)
        self.progress_label.configure(text=f"{downloaded_bytes/1024/1024:.2f} MB / {self.total_size/1024/1024:.2f} MB")
        self.percentage_complete.configure(text=f"{str(done*100).split('.')[0]}%")
        self.download_speed_label.configure(text=f"{avg_speed/1024/1024:.2f} MB/s")
        self.eta_label.configure(text=f"ETA: {time_left_str}")
        self.time_at_start_of_chunk = time.perf_counter()
        #print(f"Current: {speed/1024/1024:.2f} MB/s")
        #print(f"Avg: {avg_speed/1024/1024:.2f} MB/s")

    def cancel_button_event(self, skip_confirmation=False):
        start_time = time.perf_counter()
        self.cancel_download_raised = True
        if skip_confirmation and messagebox.askyesno("Confirmation","Are you sure you want to cancel this download?"):
            self.cancel_download_button.configure(text="Cancelled", state="disabled")
            self.install_status_label.configure(text="Status: Cancelled")
            return True
        else:
            self.time_during_cancel = time.perf_counter() - start_time
            return False
        
            
    def update_extraction_progress(self, value):
        self.progress_bar.set(value)
        self.percentage_complete.configure(text=f"{str(value*100).split('.')[0]}%")
            
    def installation_interrupted(self, error):
        self.cancel_download_raised = True
        self.cancel_download_button.configure(state="disabled")
        self.install_status_label.configure(text=f"Encountered error: {error}")
    def skip_to_installation(self):
        self.download_name.configure(text=f"{self.download_name.cget('text')} (Not downloaded through app)")
        self.download_speed_label.grid_forget()
        self.eta_label.grid_forget()
        self.cancel_download_button.configure(state="disabled")
        self.progress_label.grid_forget()
    
            
    def complete_download(self, emulator):
        self.cancel_download_button.configure(state="disabled")
        self.install_status_label.configure(text=f"Status: Installing for {emulator}....")
        self.progress_bar.set(0)
        self.percentage_complete.configure(text="0%")
    def finish_installation(self):
        minutes, seconds = divmod(int(time.perf_counter()-self.start_time), 60)
        hours, minutes = divmod(minutes, 60)
        elapsed_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        self.install_status_label.configure(text="Status: Complete")
        self.download_speed_label.configure(text=f"Elapsed time: {elapsed_time}")
        messagebox.showinfo("Download Complete", f"{self.filename} has been installed")
        
   
        
class Application(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.title("SwitchEmuTool")
        self.delete_download=tk.BooleanVar()
        self.chunk_size = customtkinter.IntVar()
        self.chunk_size.set(1024*512)
        self.geometry("839x519")
        self.resizable(False, False)
        self.fetched_versions=0
        self.fetching_versions=False
        self.firmware_installation_in_progress = False
        self.key_installation_in_progress = False
        self.retries_attempted = 0
        self.error_fetching_versions = False
        self.downloads_in_progress = 0
        self.tabview=customtkinter.CTkTabview(self)
        self.tabview.add("Both")
        self.tabview.add("Firmware")
        self.tabview.add("Keys")
        self.tabview.add("Downloads")
        self.tabview.grid(row=1, column=0, padx=20, pady=20)
        self.firmware_versions_frame = customtkinter.CTkScrollableFrame(self.tabview.tab("Firmware"), width=700, height=400)
        self.firmware_versions_frame.grid(row=0, column=0)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self.firmware_versions_frame.grid_columnconfigure(0, weight=1)
        
        self.key_versions_frame = customtkinter.CTkScrollableFrame(self.tabview.tab("Keys"), width=700, height=400)
        self.key_versions_frame.grid(row=0, column=0)
        self.key_versions_frame.grid_columnconfigure(0, weight=1)
        
        self.both_versions_frame = customtkinter.CTkScrollableFrame(self.tabview.tab("Both"), width=700, height=400)
        self.both_versions_frame.grid(row=0, column=0)
        self.both_versions_frame.grid_columnconfigure(0, weight=1)
        
        self.downloads_frame = customtkinter.CTkScrollableFrame(self.tabview.tab("Downloads"), width=700, height=400)
        self.downloads_frame.grid(row=0, column=0)
        self.downloads_frame.grid_columnconfigure(0, weight=1)
        
        self.menu = tk.Menu(self.master, tearoff="off")
        self.config(menu=self.menu)
        self.file_menu = tk.Menu(self.menu, tearoff="off")
        self.menu.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="Install Firmware from ZIP", command=self.install_from_zip_button)
        self.delete_download = customtkinter.BooleanVar()
        self.delete_download.set(True)
        self.options_menu = tk.Menu(self.menu, tearoff="off")
        self.menu.add_cascade(label="Options", menu=self.options_menu)
        self.options_menu.add_checkbutton(label="Delete files after installing", offvalue=False, onvalue=True, variable=self.delete_download)
        
        
        self.emulator_choice=customtkinter.StringVar()
        self.emulator_choice.set("Both")
        self.download_options = tk.Menu(self.menu, tearoff="off")
        self.download_options.add_radiobutton(label="Yuzu", value="Yuzu", variable=self.emulator_choice)
        self.download_options.add_radiobutton(label="Ryujinx", value="Ryujinx", variable=self.emulator_choice)
        self.download_options.add_radiobutton(label="Both", value="Both", variable=self.emulator_choice)
        self.options_menu.add_cascade(label="Install files for...", menu=self.download_options)
        self.chunk_size_menu = tk.Menu(self.menu, tearoff="off")
        chunk_size = 4096
        for i in range(10):

            self.chunk_size_menu.add_radiobutton(label=str(chunk_size), value=chunk_size, variable=self.chunk_size)
            chunk_size=chunk_size*2
        #self.portable_
        download_folder = os.path.join(os.getcwd(), "EmuToolDownloads")
        self.options_menu.add_cascade(label="Choose chunk size...", menu=self.chunk_size_menu)
        if not os.path.exists(download_folder):
            os.makedirs(download_folder)
        self.fetch_versions()
        self.mainloop()
    
        

    def fetch_versions(self):
        
        if self.fetching_versions:
            messagebox.showerror("EmuTool","A version fetch is already in progress!")
            return
        self.fetching_versions=True
        self.fetched_versions=0
        self.error_encountered = None
        self.error_fetching_versions = False
        threading.Thread(target=self.fetch_firmware_versions).start()
        threading.Thread(target=self.fetch_key_versions).start()
        threading.Thread(target=self.display_both_versions).start()
        
            
        
        
    def display_both_versions(self):  
        while self.fetched_versions<2:
            if self.error_fetching_versions:
                
                    
                
                self.fetching_versions = False
                if self.retries_attempted < 3 and messagebox.askretrycancel("Error", f"Error while fetching versions. Retry?\n\nFull Error: {self.error_encountered}" ):
                    self.retries_attempted+=1
                    self.fetch_versions()
                    return
                else:
                    quit()
                
            time.sleep(1)
        count=0
        for firmware_version in self.firmware_versions:
            for key_version in self.key_versions:
                if firmware_version[0].split("Firmware ")[-1] == key_version[0].split("Keys ")[-1]:
            
                    version = key_version[0].split("Keys ")[-1]
                    links=[key_version[1], firmware_version[1]]
                    version_label = customtkinter.CTkLabel(self.both_versions_frame, text=version)
                    version_label.grid(row=count, column=0, pady=10, sticky="W")
                    version_button = customtkinter.CTkButton(self.both_versions_frame, text="Download", command=lambda links=links: self.download(links, mode="Both"))
                    version_button.grid(row=count, column=1, pady=10, sticky="E")
                    count+=1
        self.fetching_versions=False
                
                
                    
    def fetch_firmware_versions(self):
        
       

       
        url = base64.b64decode('aHR0cHM6Ly9kYXJ0aHN0ZXJuaWUubmV0L3N3aXRjaC1maXJtd2FyZXMv'.encode("ascii")).decode("ascii")
        try:
            page = requests.get(url)
        except Exception as e:
            self.error_fetching_versions = True
            self.error_encountered = e
            
            return
        soup = BeautifulSoup(page.content, "html.parser")

        self.firmware_versions = []
        
        for link in soup.find_all("a"):
            if ('.zip' in link.get('href', []) and 'global' in link['href']):
                version=link['href'].split('/')[-1].split('.zip')[-2]
                self.firmware_versions.append((unquote(version),link))
        self.display_firmware_versions(self.firmware_versions)

    def fetch_key_versions(self):  
        url = "https://github.com/Viren070/SwitchFirmwareKeysInstaller/blob/main/Keys/keys.md"
        try:
            page = requests.get(url)
        except Exception as e:
            self.error_fetching_versions = True
            self.error_encountered = e
            return
        soup = BeautifulSoup(page.content, "html.parser")

        self.key_versions = []
        
        for link in soup.find_all("a"):
            
            if '.keys' in link.get('href', []):
                version=re.sub('<[^>]+>', '', str(link))
                
                self.key_versions.append((unquote(version),link))
        self.display_key_versions(self.key_versions)
        
        
    def display_firmware_versions(self, versions):
        for widget in self.firmware_versions_frame.winfo_children():
            widget.grid_forget()

        for i ,(version, link) in enumerate(versions):
            version_label = customtkinter.CTkLabel(self.firmware_versions_frame, text=version)
            version_label.grid(row=i, column=0, pady=10, sticky="W")
            version_button = customtkinter.CTkButton(self.firmware_versions_frame, text="Download", command=lambda link=link: self.download(link, mode="Firmware"))
            version_button.grid(row=i, column=1, pady=10, sticky="E")
        self.fetched_versions+=1
    def display_key_versions(self, versions):
        for widget in self.key_versions_frame.winfo_children():
            widget.grid_forget()
        for i,(version, link) in enumerate(versions):
            version_label = customtkinter.CTkLabel(self.key_versions_frame, text=version)
            version_label.grid(row=i, column=0, pady=10, sticky="W")
            version_button = customtkinter.CTkButton(self.key_versions_frame, text="Download", command=lambda link=link: self.download(link, mode="Keys"))
            version_button.grid(row=i, column=1, pady=10, sticky="E")
        self.fetched_versions+=1
            
        
    
    def download(self, link, mode):
        self.tabview.set("Downloads")
        if mode=="Both":
            if self.key_installation_in_progress or self.firmware_installation_in_progress:
                messagebox.showerror("Error","There is already a firmware or key installation in progress!")
                return
        
            threading.Thread(target=self.download_both, args=(link,)).start()
        elif mode == "Keys":
            if self.key_installation_in_progress:
                messagebox.showerror("Error","There is already a key installation in progress!")
                return
            
            threading.Thread(target=self.download_keys, args=(link,)).start()
        elif mode == "Firmware":
            if self.firmware_installation_in_progress:
                messagebox.showerror("Error","There is already a firmware installation in progress!")
                return
            
            threading.Thread(target=self.download_firmware, args=(link,)).start()
        

    def download_both(self, links):
        self.download_keys(links[0])
        self.download_firmware(links[1])
   
   
    def download_keys(self, link):
        self.downloads_in_progress+=1
        self.key_installation_in_progress = True
        try:
            download_result = self.download_from_link(link['href'], re.sub('<[^>]+>', '', str(link))) 
        except Exception as e:
            messagebox.showerror("Error",e)
            self.key_installation_in_progress = False
            return
        if download_result is not None:
            downloaded_file = download_result[0]
            status_frame = download_result[1]
            if self.emulator_choice.get() == "Both":
                try:
                    self.install_keys("Yuzu", downloaded_file, status_frame)
                    self.install_keys("Ryujinx", downloaded_file, status_frame)
                except Exception as e:
                    messagebox.showerror("Error",e)
                    self.key_installation_in_progress = False
                    return
            else:
                try:
                    self.install_keys(self.emulator_choice.get(), downloaded_file, status_frame)
                except Exception as e:
                    messagebox.showerror("Error", e)
                    self.key_installation_in_progress = False
                    return
                
                    
                    
        status_frame.finish_installation()
        self.key_installation_in_progress = False
        if self.delete_download.get():
            os.remove(downloaded_file)
        
        
        
    
    def install_keys(self, emulator, keys, status_frame = None):
        if status_frame is not None: status_frame.complete_download(emulator)
        dst_folder = os.path.join(os.path.join(os.getenv('APPDATA'), emulator), "keys") if emulator=="Yuzu" else os.path.join(os.path.join(os.getenv('APPDATA'), emulator), "system")
        if not os.path.exists(dst_folder): os.makedirs(dst_folder)
        dst_file = os.path.join(dst_folder, "prod.keys")
        if os.path.exists(dst_file): os.remove(dst_file)
        shutil.copy(keys, dst_folder)
        if status_frame is not None: status_frame.update_extraction_progress(1)
                        
    
    def download_firmware(self, link):
        self.downloads_in_progress+=1
        self.firmware_installation_in_progress = True
        try:
            download_result = self.download_from_link(link['href'], unquote(link['href'].split('/')[-1].split('.zip')[-2]))
        except Exception as e:
            messagebox.showerror("Error",e)
            self.firmware_installation_in_progress = False
            return 
        if download_result is not None:
            downloaded_file = download_result[0]
            status_frame = download_result[1]
            if self.emulator_choice.get() == "Both":
                try:
                    self.install_firmware("Yuzu", downloaded_file, status_frame)
                    self.install_firmware("Ryujinx", downloaded_file, status_frame)
                    status_frame.finish_installation()
                except Exception as e:
                    messagebox.showerror("ERROR",f"{e}")
                    status_frame.installation_interrupted(e)
                    self.firmware_installation_in_progress = False
                    return 
            else:
                try:
                    self.install_firmware(self.emulator_choice.get(), downloaded_file, status_frame)
                    status_frame.finish_installation()
                except Exception as e:
                    messagebox.showerror("Error", e)
                    status_frame.installation_interrupted(e)
                    self.firmware_installation_in_progress = False
                
            if self.delete_download.get():
                os.remove(downloaded_file)  
                
        self.firmware_installation_in_progress = False
       

    def install_firmware(self, emulator, firmware_source, status_frame = None):
        emulator_folder = os.path.join(os.getenv('APPDATA'), emulator)
        if status_frame is not None: 
            status_frame.complete_download(emulator)
        if emulator == "Ryujinx":
            install_directory= os.path.join(emulator_folder, r'bis\system\Contents\registered')
        elif emulator == "Yuzu":
            install_directory= os.path.join(emulator_folder, r'nand\system\Contents\registered')
        
            
        _, ext = os.path.splitext(firmware_source)
        with open(firmware_source, 'rb') as file:
            if ext == ".zip":
              
                with zipfile.ZipFile(file) as archive:
                    self.extract_from_zip(archive, install_directory, emulator, status_frame)
            else:
                raise Exception("Error: Firmware file is not a zip file.")
                
        
        
        
        
    def install_from_zip_button(self):
        path_to_zip = filedialog.askopenfilename(filetypes=[("Zip files", "*.zip")])
        if path_to_zip is not None and path_to_zip != "": 
            if self.emulator_choice.get() == "Both":
                try:
                    self.install_firmware("Yuzu", path_to_zip)
                    self.install_firmware("Ryujinx", path_to_zip)
                except Exception as e:
                    messagebox.showerror("Error", e)
                
            else:
                try:
                    self.install_firmware(self.emulator_choice.get(), path_to_zip)
                except Exception as e:
                    messagebox.showerror("Error", e)
                
            
        


    def extract_from_zip(self, archive, install_directory, emulator, status_frame = None):
        self.delete_files_and_folders(install_directory)
        total_files = len(archive.namelist())
        extracted_files = 0
        for entry in archive.infolist():
            if entry.filename.endswith('.nca') or entry.filename.endswith('.nca/00'):
                path_components = entry.filename.replace('.cnmt', '').split('/')
                nca_id = path_components[-1]

                if nca_id == '00':
                    nca_id = path_components[-2]

                if '.nca' in nca_id:
                    if emulator=="Ryujinx":
                        new_path = os.path.join(install_directory, nca_id)
                        os.makedirs(new_path, exist_ok=True)
                        with open(os.path.join(new_path, '00'), 'wb') as f:
                            f.write(archive.read(entry))
                    elif emulator=="Yuzu":
                        new_path = os.path.join(install_directory, nca_id)
                        with open(new_path, 'wb') as f:
                            f.write(archive.read(entry))
                    extracted_files+=1
                    if status_frame is not None:
                        status_frame.update_extraction_progress(extracted_files / total_files)
                        
            else:
                
                raise Exception("Error: ZIP file is not a firmware file or contains other files.")
        
       
    def download_from_link(self, link, filename):
       
        download_status_frame = DownloadStatusFrame(self.downloads_frame, filename)
        download_status_frame.grid(row=self.downloads_in_progress, column=0, sticky="EW", pady=20)
        filename = unquote(link.split('/')[-1])
        
        #link = "https://speed.hetzner.de/1GB.bin"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36 OPR/97.0.0.0',
            'Accept-Encoding': 'identity'  # Disable compression
        }
        session = requests.Session()
        response=session.get(link, headers=headers, stream=True)
        response.raise_for_status()
        #response=requests.get(link, headers=headers, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        file_path = os.path.join(os.path.join(os.getcwd(), "EmuToolDownloads"), filename)    
        with io.BytesIO() as f:
            
          
            download_status_frame.start_time = time.perf_counter()
            download_status_frame.total_size = total_size
            download_status_frame.time_at_start_of_chunk = time.perf_counter()
            if total_size is None:
                f.write(response.content)
            else:
                downloaded_bytes=0
                chunk_size=self.chunk_size.get()
                for data in response.iter_content(chunk_size=chunk_size):
                    if download_status_frame.cancel_download_raised:
                        if download_status_frame.cancel_button_event(True):
                            raise Exception("Download cancelled by user")
                        else:
                            download_status_frame.cancel_download_raised = False
                    
                    downloaded_bytes+=len(data)
                    f.write(data)
                    
                        
                    download_status_frame.update_download_progress(downloaded_bytes, chunk_size)
               
            if downloaded_bytes != total_size:
                download_status_frame.destroy()
                self.downloads_in_progress -= 1
                raise Exception(f"File was not completely downloaded {downloaded_bytes}/{total_size}\n Exited after {time.perf_counter() - download_status_frame.start_time} s.")

            with open(file_path, 'wb') as file:
                file.write(f.getvalue())
        
        return file_path, download_status_frame
    
    def delete_files_and_folders(self, directory):
        for root, dirs, files in os.walk(directory, topdown=False):
            for file in files:
                os.remove(os.path.join(root, file))
            for folder in dirs:
                os.rmdir(os.path.join(root, folder))
    

if __name__ == "__main__":
    Application()               



           
