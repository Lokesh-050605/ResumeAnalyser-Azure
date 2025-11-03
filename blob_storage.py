from azure.storage.blob import BlobServiceClient, ContentSettings
from azure.core.exceptions import AzureError

class BlobStorageClient:
    def __init__(self, connection_string, container_name):
        self.connection_string = connection_string
        self.container_name = container_name
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        self.container_client = self.blob_service_client.get_container_client(container_name)
        
        # Create container if it doesn't exist
        try:
            self.container_client.create_container()
        except Exception as e:
            # Container already exists or other error
            pass
    
    def upload_file(self, blob_name, file_content):
        """Upload file to blob storage and return URL"""
        try:
            blob_client = self.container_client.get_blob_client(blob_name)
            
            # Determine content type
            content_type = 'application/pdf' if blob_name.endswith('.pdf') else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            
            blob_client.upload_blob(
                file_content,
                overwrite=True,
                content_settings=ContentSettings(content_type=content_type)
            )
            
            return blob_client.url
        except AzureError as e:
            raise Exception(f"Failed to upload to blob storage: {str(e)}")
    
    def download_file(self, blob_name):
        """Download file from blob storage and return bytes"""
        try:
            blob_client = self.container_client.get_blob_client(blob_name)
            download_stream = blob_client.download_blob()
            return download_stream.readall()
        except AzureError as e:
            raise Exception(f"Failed to download from blob storage: {str(e)}")
    
    def list_blobs(self, prefix=None):
        """List all blobs with optional prefix"""
        try:
            blobs = self.container_client.list_blobs(name_starts_with=prefix)
            return [blob.name for blob in blobs]
        except AzureError as e:
            raise Exception(f"Failed to list blobs: {str(e)}")
    
    def delete_blob(self, blob_name):
        """Delete a blob"""
        try:
            blob_client = self.container_client.get_blob_client(blob_name)
            blob_client.delete_blob()
            return True
        except AzureError as e:
            raise Exception(f"Failed to delete blob: {str(e)}")