import os
import glob
import json
import mimetypes
from aiogoogle import Aiogoogle

class AsyncDriveUploader:
    def __init__(self, credentials_path):
        """
        Initialize Aiogoogle with user credentials
        
        Args:
            credentials_path (str): Path to OAuth 2.0 credentials file
        """
        with open(credentials_path, "r", encoding="utf-8") as json_file:
            creds_data = json.load(json_file)
        self.user = {"access_token": creds_data['token'], "refresh_token": creds_data['refresh_token']}
        self.client = {"client_id": creds_data['client_id'], "client_secret": creds_data['client_secret'], "scopes": creds_data['scopes']}

    async def get_or_create_folder(self, folder_name, parent_folder_id=None):
        """
        Find or create a folder in Google Drive.
        
        Args:
            folder_name (str): Name of the folder to find or create
            parent_folder_id (str, optional): ID of parent folder
        
        Returns:
            str: Folder ID
        """
        async with Aiogoogle(user_creds=self.user, client_creds=self.client) as aiogoogle:
            drive_v3 = await aiogoogle.discover('drive', 'v3')
            
            # Build query to find folder
            query = [f"name='{folder_name}'", "mimeType='application/vnd.google-apps.folder'"]
            if parent_folder_id:
                query.append(f"'{parent_folder_id}' in parents")
            
            # Search for existing folder
            results = await aiogoogle.as_user(
                drive_v3.files.list(
                    q=' and '.join(query),
                    spaces='drive'
                )
            )
            
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
            
            folder = await aiogoogle.as_user(
                drive_v3.files.create(
                    json=folder_metadata, 
                    fields='id'
                )
            )
            
            return folder['id']

    async def make_public_with_link(self, file_or_folder_id):
        """
        Make a file or folder publicly accessible and get a shareable link.
        
        Args:
            file_or_folder_id (str): ID of the file or folder
        
        Returns:
            str: Public sharing link
        """
        async with Aiogoogle(user_creds=self.user, client_creds=self.client) as aiogoogle:
            drive_v3 = await aiogoogle.discover('drive', 'v3')
            
            try:
                # Create a public permission
                await aiogoogle.as_user(
                    drive_v3.permissions.create(
                        fileId=file_or_folder_id,
                        json={'type': 'anyone', 'role': 'reader'}
                    )
                )
                
                # Get the file/folder details to retrieve the web view link
                file_metadata = await aiogoogle.as_user(
                    drive_v3.files.get(
                        fileId=file_or_folder_id, 
                        fields='webViewLink'
                    )
                )
                
                return file_metadata.get('webViewLink', None)
            
            except Exception as e:
                print(f"Error making file/folder public: {e}")
                return None

    async def batch_upload(self, paths, folder_in_drive='Uploaded', make_public=False, recursive=False):
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
        root_folder_id = await self.get_or_create_folder(folder_in_drive)
        
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
                        result = await self._upload_single_file(
                            matched_path, 
                            root_folder_id, 
                            make_public
                        )
                        upload_results.append(result)
                    
                    elif os.path.isdir(matched_path):
                        # Upload folder
                        if recursive:
                            result = await self._upload_folder(
                                matched_path, 
                                root_folder_id, 
                                make_public
                            )
                        else:
                            # Non-recursive folder upload (only files in root)
                            result = await self._upload_non_recursive_folder(
                                matched_path, 
                                root_folder_id, 
                                make_public
                            )
                        upload_results.append(result)
                
                except Exception as e:
                    print(f"Error uploading {matched_path}: {e}")
        
        return upload_results

    async def _upload_single_file(self, file_path, parent_folder_id=None, make_public=False):
        """
        Upload a single file to Google Drive.
        
        Args:
            file_path (str): Path to the file to upload
            parent_folder_id (str, optional): ID of parent folder
            make_public (bool, optional): Whether to make the file public
        
        Returns:
            dict: Information about uploaded file
        """
        async with Aiogoogle(user_creds=self.user, client_creds=self.client) as aiogoogle:
            drive_v3 = await aiogoogle.discover('drive', 'v3')
            
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
            
            # Upload the file
            print(file_path)
            file = await aiogoogle.as_user(
                drive_v3.files.create(
                    json=file_metadata,
                    upload_file=file_path,
                    fields='id,webViewLink'
                )
            )
            
            # Make file public if requested
            public_link = None
            if make_public:
                public_link = await self.make_public_with_link(file['id'])
            
            return {
                'type': 'file',
                'name': os.path.basename(file_path),
                'full_path': file_path,
                'id': file['id'],
                'size_bytes': file_size,
                'size_human_readable': self._format_file_size(file_size),
                'link': public_link or file.get('webViewLink')
            }

    async def _upload_folder(self, local_path, parent_folder_id=None, make_public=False):
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
        current_folder_id = await self.get_or_create_folder(
            folder_name, 
            parent_folder_id
        )
        
        # Make folder public if requested
        public_link = None
        if make_public:
            public_link = await self.make_public_with_link(current_folder_id)
        
        # Track uploaded files
        uploaded_files = []
        total_size = 0
        
        # Iterate through all files and subdirectories
        for item in os.listdir(local_path):
            local_item_path = os.path.join(local_path, item)
            
            # Recursively upload files and subdirectories
            if os.path.isfile(local_item_path):
                file_result = await self._upload_single_file(
                    local_item_path, 
                    current_folder_id, 
                    make_public
                )
                total_size += file_result.get('size_bytes', 0)
                uploaded_files.append(file_result)
            elif os.path.isdir(local_item_path):
                subfolder_result = await self._upload_folder(
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

    async def _upload_non_recursive_folder(self, local_path, parent_folder_id=None, make_public=False):
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
        current_folder_id = await self.get_or_create_folder(
            folder_name, 
            parent_folder_id
        )
        
        # Make folder public if requested
        public_link = None
        if make_public:
            public_link = await self.make_public_with_link(current_folder_id)
        
        # Track uploaded files
        uploaded_files = []
        total_size = 0
        
        # Upload only files in the root of the folder
        for item in os.listdir(local_path):
            local_item_path = os.path.join(local_path, item)
            
            # Upload only files, skip subdirectories
            if os.path.isfile(local_item_path):
                file_result = await self._upload_single_file(
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