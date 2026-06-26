import azure.functions as func
import datetime
import json
import logging
import os
from azure.storage.blob import BlobServiceClient
from io import BytesIO

app = func.FunctionApp()

@app.route(route="health", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def health(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    return func.HttpResponse(f"Hello, what would you like to offer?", status_code=200)

@app.route(route="receive", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def receive(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('File upload request received.')
    
    try:
        # Get all uploaded files from the request
        files = [file for key in req.files.keys() for file in req.files.getlist(key)]
        
        if not files or len(files) == 0:
            return func.HttpResponse(
                json.dumps({"error": "No file provided. Please upload a file with key 'file'"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Get Azure Storage connection string
        connection_string = os.environ.get('AzureWebJobsStorage')
        if not connection_string:
            logging.error("AzureWebJobsStorage connection string not found")
            return func.HttpResponse(
                json.dumps({"error": "Storage configuration error"}),
                status_code=500,
                mimetype="application/json"
            )
        
        # Get container name from environment or use default
        container_name = os.environ.get('STORAGE_CONTAINER_NAME', 'uploads')
        
        # Initialize blob service client
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        
        # Ensure container exists
        try:
            container_client = blob_service_client.get_container_client(container_name)
            if not container_client.exists():
                container_client.create_container()
                logging.info(f"Created container: {container_name}")
        except Exception as e:
            logging.error(f"Error accessing container: {str(e)}")
            return func.HttpResponse(
                json.dumps({"error": "Storage container error"}),
                status_code=500,
                mimetype="application/json"
            )
        
        uploaded_files = []
        
        # Upload each file
        for file in files:
            filename = file.filename
            if not filename:
                continue
                
            # Generate unique blob name with timestamp
            timestamp = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            blob_name = f"{timestamp}_{filename}"
            
            # Get blob client
            blob_client = blob_service_client.get_blob_client(
                container=container_name,
                blob=blob_name
            )
            
            # Read file content
            file_content = file.read()
            
            # Upload to blob storage
            blob_client.upload_blob(file_content, overwrite=True)
            
            logging.info(f"File uploaded successfully: {blob_name}")
            
            uploaded_files.append({
                "original_name": filename,
                "blob_name": blob_name,
                "size_bytes": len(file_content),
                "container": container_name
            })
        
        return func.HttpResponse(
            json.dumps({
                "message": "Files uploaded successfully",
                "files": uploaded_files
            }),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Error processing file upload: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Failed to process upload: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )