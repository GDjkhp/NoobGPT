import os
import glob
import mimetypes
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

class DriveUploader:
    def __init__(self, credentials_path):
        """
        Initialize Google Drive service
        
        Args:
            credentials_path (str): Path to OAuth 2.0 credentials file
        """
        self.creds = Credentials.from_authorized_user_file(
            credentials_path, 
            ['https://www.googleapis.com/auth/drive.file']
        )
        self.drive_service = build('drive', 'v3', credentials=self.creds)

    def get_or_create_folder(self, folder_name, parent_folder_id=None):
        """
        Find or create a folder in Google Drive.
        
        Args:
            folder_name (str): Name of the folder to find or create
            parent_folder_id (str, optional): ID of parent folder
        
        Returns:
            str: Folder ID
        """
        # Build query to find folder
        query = [f"name='{folder_name}'", "mimeType='application/vnd.google-apps.folder'"]
        if parent_folder_id:
            query.append(f"'{parent_folder_id}' in parents")
        
        results = self.drive_service.files().list(
            q=' and '.join(query),
            spaces='drive'
        ).execute()
        
        folders = results.get('files', [])
        
        # If folder exists, return its ID
        if folders:
            return folders[0]['id']
        
        # If folder doesn't exist, create it
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        # Add parent if specified
        if parent_folder_id:
            folder_metadata['parents'] = [parent_folder_id]
        
        folder = self.drive_service.files().create(
            body=folder_metadata, 
            fields='id'
        ).execute()
        
        return folder['id']

    def make_public_with_link(self, file_or_folder_id):
        """
        Make a file or folder publicly accessible and get a shareable link.
        
        Args:
            file_or_folder_id (str): ID of the file or folder
        
        Returns:
            str: Public sharing link
        """
        try:
            # Create a public permission
            self.drive_service.permissions().create(
                fileId=file_or_folder_id,
                body={'type': 'anyone', 'role': 'reader'}
            ).execute()
            
            # Get the file/folder details to retrieve the web view link
            file_metadata = self.drive_service.files().get(
                fileId=file_or_folder_id, 
                fields='webViewLink'
            ).execute()
            
            return file_metadata.get('webViewLink', None)
        
        except Exception as e:
            print(f"Error making file/folder public: {e}")
            return None

    def batch_upload(self, paths, folder_in_drive='Uploaded', make_public=False, recursive=False):
        """
        Batch upload multiple files and folders.
        
        Args:
            paths (list): List of file or folder paths to upload
            folder_in_drive (str, optional): Parent folder name in Drive
            make_public (bool, optional): Whether to make content public
            recursive (bool, optional): Whether to recursively upload folder contents
        
        Returns:
            list: List of upload results
        """
        # Get or create the root folder in Drive
        root_folder_id = self.get_or_create_folder(folder_in_drive)
        
        # Results storage
        upload_results = []
        
        # Process each path
        for path in paths:
            # Expand glob patterns
            matching_paths = glob.glob(path)
            
            for matched_path in matching_paths:
                try:
                    # Check if path exists
                    if not os.path.exists(matched_path):
                        print(f"Path not found: {matched_path}")
                        continue
                    
                    # Determine upload method based on path type
                    if os.path.isfile(matched_path):
                        # Upload single file
                        result = self._upload_single_file(
                            matched_path, 
                            root_folder_id, 
                            make_public
                        )
                        upload_results.append(result)
                    
                    elif os.path.isdir(matched_path):
                        # Upload folder
                        if recursive:
                            result = self._upload_folder(
                                matched_path, 
                                root_folder_id, 
                                make_public
                            )
                        else:
                            # Non-recursive folder upload (only files in root)
                            result = self._upload_non_recursive_folder(
                                matched_path, 
                                root_folder_id, 
                                make_public
                            )
                        upload_results.append(result)
                
                except Exception as e:
                    print(f"Error uploading {matched_path}: {e}")
        
        return upload_results

    def _upload_single_file(self, file_path, parent_folder_id=None, make_public=False):
        """
        Upload a single file to Google Drive.
        
        Args:
            file_path (str): Path to the file to upload
            parent_folder_id (str, optional): ID of parent folder
            make_public (bool, optional): Whether to make the file public
        
        Returns:
            dict: Information about uploaded file
        """
        # Get file size
        file_size = os.path.getsize(file_path)

        # Prepare file metadata
        file_metadata = {
            'name': os.path.basename(file_path)
        }
        
        # Add parent folder if specified
        if parent_folder_id:
            file_metadata['parents'] = [parent_folder_id]
        
        # Detect MIME type
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type is None:
            mime_type = 'application/octet-stream'
        
        # Create media upload
        media = MediaFileUpload(
            file_path, 
            mimetype=mime_type, 
            resumable=True
        )
        
        # Upload the file
        print(file_path)
        file = self.drive_service.files().create(
            body=file_metadata, 
            media_body=media, 
            fields='id,webViewLink'
        ).execute()
        
        # Make file public if requested
        public_link = None
        if make_public:
            public_link = self.make_public_with_link(file['id'])
        
        return {
            'type': 'file',
            'name': os.path.basename(file_path),
            'full_path': file_path,
            'id': file['id'],
            'size_bytes': file_size,
            'size_human_readable': self._format_file_size(file_size),
            'link': public_link or file.get('webViewLink')
        }

    def _upload_folder(self, local_path, parent_folder_id=None, make_public=False):
        """
        Recursively upload a local folder to Google Drive.
        
        Args:
            local_path (str): Path to local folder to upload
            parent_folder_id (str, optional): ID of parent folder in Drive
            make_public (bool, optional): Whether to make the folder public
        
        Returns:
            dict: Information about uploaded folder
        """
        # Get the base folder name
        folder_name = os.path.basename(local_path)
        
        # Create the folder in Google Drive
        current_folder_id = self.get_or_create_folder(
            folder_name, 
            parent_folder_id
        )
        
        # Make folder public if requested
        public_link = None
        if make_public:
            public_link = self.make_public_with_link(current_folder_id)
        
        # Track uploaded files
        uploaded_files = []
        total_size = 0
        
        # Iterate through all files and subdirectories
        for item in os.listdir(local_path):
            local_item_path = os.path.join(local_path, item)
            
            # Recursively upload files and subdirectories
            if os.path.isfile(local_item_path):
                file_result = self._upload_single_file(
                    local_item_path, 
                    current_folder_id, 
                    make_public
                )
                total_size += file_result.get('size_bytes', 0)
                uploaded_files.append(file_result)
            elif os.path.isdir(local_item_path):
                subfolder_result = self._upload_folder(
                    local_item_path, 
                    current_folder_id, 
                    make_public
                )
                total_size += subfolder_result.get('size_bytes', 0)
                uploaded_files.append(subfolder_result)
        
        return {
            'type': 'folder',
            'folder_id': current_folder_id,
            'name': folder_name,
            'full_path': local_path,
            'link': public_link,
            'size_bytes': total_size,
            'size_human_readable': self._format_file_size(total_size),
            'files': uploaded_files
        }

    def _upload_non_recursive_folder(self, local_path, parent_folder_id=None, make_public=False):
        """
        Upload only files in the root of a folder (non-recursive).
        
        Args:
            local_path (str): Path to local folder to upload
            parent_folder_id (str, optional): ID of parent folder in Drive
            make_public (bool, optional): Whether to make the folder public
        
        Returns:
            dict: Information about uploaded folder
        """
        # Get the base folder name
        folder_name = os.path.basename(local_path)
        
        # Create the folder in Google Drive
        current_folder_id = self.get_or_create_folder(
            folder_name, 
            parent_folder_id
        )
        
        # Make folder public if requested
        public_link = None
        if make_public:
            public_link = self.make_public_with_link(current_folder_id)
        
        # Track uploaded files
        uploaded_files = []
        total_size = 0
        
        # Upload only files in the root of the folder
        for item in os.listdir(local_path):
            local_item_path = os.path.join(local_path, item)
            
            # Upload only files, skip subdirectories
            if os.path.isfile(local_item_path):
                file_result = self._upload_single_file(
                    local_item_path, 
                    current_folder_id, 
                    make_public
                )
                total_size += file_result.get('size_bytes', 0)
                uploaded_files.append(file_result)
        
        return {
            'type': 'folder',
            'folder_id': current_folder_id,
            'name': folder_name,
            'full_path': local_path,
            'link': public_link,
            'size_bytes': total_size,
            'size_human_readable': self._format_file_size(total_size),
            'files': uploaded_files
        }

    def _format_file_size(self, size_bytes):
        """
        Convert file size in bytes to human-readable format.
        
        Args:
            size_bytes (int): Size in bytes
        
        Returns:
            str: Human-readable size
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0