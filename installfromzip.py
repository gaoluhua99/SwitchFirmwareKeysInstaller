import os
import re
import threading
import time
import tkinter as tk
import zipfile
from tkinter import filedialog, messagebox
from urllib.parse import unquote

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
        download_name = customtkinter.CTkLabel(self, text=filename)
        download_name.grid(row=0, column=0, sticky="W", padx=5)
        
        self.progress_bar = customtkinter.CTkProgressBar(self, orientation="horizontal", width=250, mode="determinate")
        self.progress_bar.grid(row=0, column=2, sticky="E", padx=5)
        self.progress_bar.set(0)

        self.percentage_complete = customtkinter.CTkLabel(self, text="0%")
        self.percentage_complete.grid(row=0, column=1, sticky="E")

        self.download_speed_label = customtkinter.CTkLabel(self, text="0 MB/s ETA: 00:00:00")
        self.download_speed_label.grid(row=1, column=2, sticky="E", padx=5)
        
        self.install_status_label = customtkinter.CTkLabel(self, text="Status: Downloading...")
        self.install_status_label.grid(row=1, column=0, sticky="W", padx=5)
        
        self.cancel_download_button = customtkinter.CTkButton(self, text="Cancel", command=self.cancel_button_event)
        self.cancel_download_button.grid(row=3,column=2, pady=10, padx=5, sticky="E")
    def update_download_progress(self, downloaded_bytes):
        
        done = downloaded_bytes / self.total_size 
        speed = downloaded_bytes / (time.perf_counter() - self.start_time)
        time_left = (self.total_size - downloaded_bytes) / speed
        
        minutes, seconds = divmod(int(time_left), 60)
        hours, minutes = divmod(minutes, 60)
        time_left_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    
       
        self.progress_bar.set(done)
        self.percentage_complete.configure(text=f"{str(done*100).split('.')[0]}%")
        self.download_speed_label.configure(text=f"{downloaded_bytes/1024/1024:.2f}/{self.total_size/1024/1024:.2f}Mb - {speed/1024/1024:.2f} Mb/s, ETA: {time_left_str}")
        
    def cancel_button_event(self, skip_confirmation=False):
        if skip_confirmation or messagebox.askyesno("Confirmation", "Are you sure you want to cancel this download?"):
            self.cancel_download_raised = True
            self.cancel_download_button.configure(text="Cancelling...", state="disabled")
            self.destroy()
    def update_extraction_progress(self, value):
        self.progress_bar.set(value)
        self.percentage_complete.configure(text=f"{str(value*100).split('.')[0]}%")
            
    def installation_interrupted(self, error):
        self.cancel_download_raised = True
        self.cancel_download_button.configure(state="disabled")
        self.install_status_label.configure(text=f"Encountered error: {error}")
        
            
    
            
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
        self.geometry("900x500")
        self.fetched_versions=0
        self.fetching_versions=False
        self.tabview=customtkinter.CTkTabview(self)
        self.tabview.add("Firmware")
        self.tabview.add("Keys")
        self.tabview.add("Both")
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
        
        self.menu = tk.Menu(self.master)
        self.config(menu=self.menu)
        self.file_menu = tk.Menu(self.menu)
        self.menu.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="Install Firmware from ZIP", command=self.install_from_zip_button)

        self.options_menu = tk.Menu(self.menu)
        self.menu.add_cascade(label="Options", menu=self.options_menu)
        self.options_menu.add_checkbutton(label="Delete files after installing", offvalue=False, onvalue=True, variable=self.delete_download)
        self.options_menu.add_command(label="Fetch versions", command=self.fetch_versions)
        
        self.emulator_choice=customtkinter.StringVar()
        self.download_options = tk.Menu(self.menu)
        self.download_options.add_radiobutton(label="Yuzu", value="Yuzu", variable=self.emulator_choice)
        self.download_options.add_radiobutton(label="Ryujinx", value="Ryujinx", variable=self.emulator_choice)
        self.download_options.add_radiobutton(label="Both", value="Both", variable=self.emulator_choice)
        self.options_menu.add_cascade(label="Install files for...", menu=self.download_options)
        
        self.fetch_versions()
        self.mainloop()
    
        

    def fetch_versions(self):
        if self.fetching_versions:
            messagebox.showerror("EmuTool","A version fetch is already in progress!")
            return
        self.fetching_versions=True
        self.fetched_versions=0
        threading.Thread(target=self.fetch_firmware_versions).start()
        threading.Thread(target=self.fetch_key_versions).start()
        threading.Thread(target=self.display_both_versions).start()
        
    def display_both_versions(self):  
        while self.fetched_versions<2:
            time.sleep(1)
        count=0
        for firmware_version in self.firmware_versions:
            for key_version in self.key_versions:
                if firmware_version[0].split("Firmware ")[-1] == key_version[0].split("Keys ")[-1]:
            
                    version = key_version[0].split("Keys ")[-1]
                    links=[firmware_version[1], key_version[1]]
                    version_label = customtkinter.CTkLabel(self.both_versions_frame, text=version)
                    version_label.grid(row=count, column=0, pady=10, sticky="W")
                    version_button = customtkinter.CTkButton(self.both_versions_frame, text="Download", command=lambda links=links: self.download(links, mode="Both"))
                    version_button.grid(row=count, column=1, pady=10, sticky="E")
                    count+=1
        self.fetching_versions=False
                
                
                    
    def fetch_firmware_versions(self):
        
       

        url = "https://darthsternie.net/switch-firmwares/"
        page = requests.get(url)
        soup = BeautifulSoup(page.content, "html.parser")

        self.firmware_versions = []
        
        for link in soup.find_all("a"):
            if ('.zip' in link.get('href', []) and 'global' in link['href']):
                version=link['href'].split('/')[-1].split('.zip')[-2]
                self.firmware_versions.append((unquote(version),link))
        self.display_firmware_versions(self.firmware_versions)

    def fetch_key_versions(self):  
        url = "https://github.com/Viren070/SwitchFirmwareKeysInstaller/blob/main/Keys/keys.md"
        page = requests.get(url)
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
        print(self.emulator_choice.get())
        if mode=="Both":
            threading.Thread(target=self.download_both, args=(link,)).start()
        elif mode == "Keys":
            threading.Thread(target=self.download_keys, args=(link,)).start()
        elif mode == "Firmware":
            threading.Thread(target=self.download_firmware, args=(link,)).start()
        

    def download_both(self, links):
        for link in links:
            self.download_from_link(link['href'], unquote(link['href'].split('/')[-1]))
    def download_keys(self, link):
        self.download_from_link(link['href'], (re.sub('<[^>]+>', '', str(link))+".zip") )
    def download_firmware(self, link):
        self.download_from_link(link['href'], unquote(link['href'].split('/')[-1]))
       
    def download_from_link(self, link, filename):
        progress_bar = customtkinter.CTkProgressBar(self.downloads_frame, orientation="horizontal", mode="determinate")
        progress_bar.grid(row=0, column=1, sticky="E")
        progress_bar.set(0)
        download_name = customtkinter.CTkLabel(self.downloads_frame, text=filename)
        download_name.grid(row=0, column=0, sticky="W")
        session = requests.Session()
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
        response=session.get(link, headers=headers, stream=True)
        response.raise_for_status()
        total_size = int(response.headers.get('content-length', 0))
        print(total_size)
        with open(filename, "wb") as f:
            if total_size is None:
                f.write(response.content)
            else:
                dl=0
                for data in response.iter_content(chunk_size=1024*1024*10):
                    dl+=len(data)
                    f.write(data)
                    print(f"{dl}/{total_size}")
                    done = (dl / int(total_size))
                    print(done)
                    progress_bar.set(done)
                    self.update_idletasks()
                    self.update()
    def install_from_zip_button(self):
        path_to_zip = filedialog.askopenfilename(filetypes=[("Zip files", "*.zip")])
        if path_to_zip is not None and path_to_zip != "": threading.Thread(target=self.open_zip, args=(path_to_zip,)).start()
        
    def open_zip(self, firmwareSource):

 
        temporaryDirectory= os.path.join(os.getenv('APPDATA'), 'Ryujinx', 'testextract')
        _, ext = os.path.splitext(firmwareSource)

        with open(firmwareSource, 'rb') as file:
            if ext == ".zip":
                with zipfile.ZipFile(file) as archive:
                    self.extract_from_zip(archive, temporaryDirectory)

    def extract_from_zip(self, archive, temporaryDirectory):
        for entry in archive.infolist():
            if entry.filename.endswith('.nca') or entry.filename.endswith('.nca/00'):
                path_components = entry.filename.replace('.cnmt', '').split('/')
                nca_id = path_components[-1]

                if nca_id == '00':
                    nca_id = path_components[-2]

                if '.nca' in nca_id:
                    new_path = os.path.join(temporaryDirectory, nca_id)
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
            if total_size is None:
                f.write(response.content)
            else:
                downloaded_bytes=0
                
                for data in response.iter_content(chunk_size=1024*512):
                    if download_status_frame.cancel_download_raised:
                        raise Exception("Download cancelled by user")
                    downloaded_bytes+=len(data)
                    f.write(data)
                    
                        
                    download_status_frame.update_download_progress(downloaded_bytes)
               
            if downloaded_bytes != total_size:
                download_status_frame.cancel_button_event(True)
                raise Exception(f"File was not completely downloaded {downloaded_bytes}/{total_size}\n Exited after {time.perf_counter() - download_status_frame.start_time} s.")

            with open(file_path, 'wb') as file:
                file.write(f.getvalue())
        

    def delete_files_and_folders(self, directory):
        for root, dirs, files in os.walk(directory, topdown=False):
            for file in files:
                os.remove(os.path.join(root, file))
            for folder in dirs:
                os.rmdir(os.path.join(root, folder))


Application()               



           