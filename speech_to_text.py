#!/usr/bin/env python3
"""
Oracle Cloud OCI Speech-to-Text Converter

This script uses Oracle Cloud Infrastructure (OCI) Speech service to convert
an audio file to text.

Prerequisites:
1. Install OCI SDK: pip install oci
2. Configure OCI credentials in ~/.oci/config
3. Have an OCI Object Storage bucket to upload the audio file
4. Have access to OCI Speech service in your tenancy

Usage:
    python speech_to_text.py
"""

import oci
import os
import sys
import time
import json
from datetime import datetime

# Configuration - Update these values with your OCI details
COMPARTMENT_ID = os.environ.get("OCI_COMPARTMENT_ID", "YOUR_COMPARTMENT_OCID")
NAMESPACE = None  # Will be auto-detected from OCI
BUCKET_NAME = os.environ.get("OCI_BUCKET_NAME", "speech-audio-bucket")
AUDIO_FILE = "New Recording.m4a"

def get_oci_config():
    """Load OCI configuration from default location or environment."""
    try:
        config = oci.config.from_file()
        oci.config.validate_config(config)
        return config
    except Exception as e:
        print(f"Error loading OCI config: {e}")
        print("\nPlease ensure you have configured OCI CLI:")
        print("1. Install OCI CLI: brew install oci-cli")
        print("2. Run: oci setup config")
        print("3. Or set up ~/.oci/config manually")
        sys.exit(1)

def upload_to_object_storage(config, namespace, bucket_name, file_path):
    """Upload audio file to OCI Object Storage."""
    print(f"\nUploading {file_path} to Object Storage...")
    
    object_storage_client = oci.object_storage.ObjectStorageClient(config)
    object_name = os.path.basename(file_path)
    
    # Read the file
    with open(file_path, 'rb') as f:
        file_content = f.read()
    
    # Upload to Object Storage
    try:
        object_storage_client.put_object(
            namespace_name=namespace,
            bucket_name=bucket_name,
            object_name=object_name,
            put_object_body=file_content,
            content_type="audio/mp4"
        )
        print(f"Successfully uploaded {object_name} to bucket {bucket_name}")
        
        # Return the Object Storage URI
        object_uri = f"oci://{bucket_name}@{namespace}/{object_name}"
        return object_uri, object_name
        
    except oci.exceptions.ServiceError as e:
        print(f"Error uploading file: {e.message}")
        if e.status == 404:
            print(f"\nBucket '{bucket_name}' not found. Please create it first:")
            print(f"  oci os bucket create -c {COMPARTMENT_ID} --name {bucket_name}")
        sys.exit(1)

def create_transcription_job(config, compartment_id, input_location):
    """Create a transcription job using OCI Speech service."""
    print("\nCreating transcription job...")
    
    speech_client = oci.ai_speech.AIServiceSpeechClient(config)
    
    # Define input location (Object Storage)
    object_location = oci.ai_speech.models.ObjectLocation(
        namespace_name=NAMESPACE,
        bucket_name=BUCKET_NAME,
        object_names=[os.path.basename(AUDIO_FILE)]
    )
    
    input_location = oci.ai_speech.models.ObjectListInlineInputLocation(
        location_type="OBJECT_LIST_INLINE_INPUT_LOCATION",
        object_locations=[object_location]
    )
    
    # Define output location
    output_location = oci.ai_speech.models.OutputLocation(
        namespace_name=NAMESPACE,
        bucket_name=BUCKET_NAME,
        prefix="transcription_output/"
    )
    
    # Create transcription job details
    create_job_details = oci.ai_speech.models.CreateTranscriptionJobDetails(
        compartment_id=compartment_id,
        display_name=f"Transcription_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        input_location=input_location,
        output_location=output_location,
        model_details=oci.ai_speech.models.TranscriptionModelDetails(
            domain="GENERIC",
            language_code="en-US"
        )
    )
    
    try:
        # Create the transcription job
        response = speech_client.create_transcription_job(
            create_transcription_job_details=create_job_details
        )
        
        job = response.data
        print(f"Transcription job created: {job.id}")
        print(f"Status: {job.lifecycle_state}")
        
        return job
        
    except oci.exceptions.ServiceError as e:
        print(f"Error creating transcription job: {e.message}")
        if "NotAuthorizedOrNotFound" in str(e):
            print("\nPlease ensure Speech service is enabled in your tenancy")
            print("and you have proper IAM policies configured.")
        sys.exit(1)

def wait_for_job_completion(config, job_id, timeout_minutes=30):
    """Wait for transcription job to complete."""
    print(f"\nWaiting for transcription job to complete (timeout: {timeout_minutes} min)...")
    
    speech_client = oci.ai_speech.AIServiceSpeechClient(config)
    
    start_time = time.time()
    timeout_seconds = timeout_minutes * 60
    
    while True:
        response = speech_client.get_transcription_job(transcription_job_id=job_id)
        job = response.data
        status = job.lifecycle_state
        
        print(f"  Status: {status}", end="\r")
        
        if status == "SUCCEEDED":
            print(f"\n✓ Transcription completed successfully!")
            return job
        elif status == "FAILED":
            print(f"\n✗ Transcription failed: {job.lifecycle_details}")
            sys.exit(1)
        elif status == "CANCELED":
            print(f"\n✗ Transcription was canceled")
            sys.exit(1)
        
        elapsed = time.time() - start_time
        if elapsed > timeout_seconds:
            print(f"\n✗ Timeout waiting for transcription")
            sys.exit(1)
        
        time.sleep(10)  # Poll every 10 seconds

def get_transcription_results(config, job):
    """Download and display transcription results."""
    print("\nRetrieving transcription results...")
    
    object_storage_client = oci.object_storage.ObjectStorageClient(config)
    
    full_transcription = []
    
    # Extract job ID suffix for the output path (format: job-{suffix})
    job_id_parts = job.id.split('.')
    job_suffix = job_id_parts[-1] if job_id_parts else job.id
    output_prefix = f"transcription_output/job-{job_suffix}"
    
    print(f"Looking for results in: {output_prefix}")
    
    # List objects with the prefix to find the output file
    list_response = object_storage_client.list_objects(
        namespace_name=NAMESPACE,
        bucket_name=BUCKET_NAME,
        prefix=output_prefix
    )
    
    for obj in list_response.data.objects:
        if obj.name.endswith('.json'):
            print(f"Found result file: {obj.name}")
            # Download the JSON file
            get_response = object_storage_client.get_object(
                namespace_name=NAMESPACE,
                bucket_name=BUCKET_NAME,
                object_name=obj.name
            )
            
            result_json = json.loads(get_response.data.content.decode('utf-8'))
            
            # Extract transcription text
            if 'transcriptions' in result_json:
                for transcription in result_json['transcriptions']:
                    if 'transcription' in transcription:
                        full_transcription.append(transcription['transcription'])
    
    return '\n'.join(full_transcription)

def save_transcription(text, output_file="transcription_output.txt"):
    """Save transcription to a text file."""
    with open(output_file, 'w') as f:
        f.write(text)
    print(f"\n✓ Transcription saved to: {output_file}")

def main():
    """Main function to orchestrate the transcription process."""
    print("=" * 60)
    print("Oracle Cloud OCI Speech-to-Text Converter")
    print("=" * 60)
    
    # Check if audio file exists
    if not os.path.exists(AUDIO_FILE):
        print(f"Error: Audio file '{AUDIO_FILE}' not found!")
        sys.exit(1)
    
    print(f"Audio file: {AUDIO_FILE}")
    print(f"File size: {os.path.getsize(AUDIO_FILE) / 1024:.2f} KB")
    
    # Load OCI configuration
    config = get_oci_config()
    print(f"Using OCI profile: {config.get('profile', 'DEFAULT')}")
    
    # Auto-detect namespace from OCI
    global NAMESPACE
    object_storage_client = oci.object_storage.ObjectStorageClient(config)
    NAMESPACE = object_storage_client.get_namespace().data
    print(f"Detected namespace: {NAMESPACE}")
    
    # Auto-detect compartment from config if not set
    global COMPARTMENT_ID
    if COMPARTMENT_ID == "YOUR_COMPARTMENT_OCID":
        COMPARTMENT_ID = config.get('tenancy')
        print(f"Using tenancy as compartment: {COMPARTMENT_ID}")
    
    # Step 1: Upload audio file to Object Storage
    object_uri, object_name = upload_to_object_storage(
        config, NAMESPACE, BUCKET_NAME, AUDIO_FILE
    )
    
    # Step 2: Create transcription job
    job = create_transcription_job(config, COMPARTMENT_ID, object_uri)
    
    # Step 3: Wait for job completion
    completed_job = wait_for_job_completion(config, job.id)
    
    # Step 4: Get transcription results
    transcription_text = get_transcription_results(config, completed_job)
    
    # Step 5: Display and save results
    print("\n" + "=" * 60)
    print("TRANSCRIPTION RESULT")
    print("=" * 60)
    print(transcription_text)
    print("=" * 60)
    
    save_transcription(transcription_text)
    
    print("\n✓ Process completed successfully!")

if __name__ == "__main__":
    main()
