# OCI Speech-to-Text Converter

This Python script uses Oracle Cloud Infrastructure (OCI) Speech service to convert audio files to text.

## Prerequisites

### 1. Oracle Cloud Account
- An active OCI account with access to the Speech service
- OCI Speech service is available in most OCI regions

### 2. Install OCI CLI and Python SDK

```bash
# Install OCI CLI (macOS)
brew install oci-cli

# Or using pip
pip install oci-cli

# Install Python dependencies
pip install -r requirements.txtpip install -r requirements.txt
```

### 3. Configure OCI Credentials

Run the OCI setup wizard:
```bash
oci setup config
```

This will prompt you for:
- **User OCID**: Found in OCI Console > Profile > User Settings
- **Tenancy OCID**: Found in OCI Console > Profile > Tenancy
- **Region**: e.g., `us-phoenix-1`, `us-ashburn-1`
- **API Key**: The wizard will generate one, or you can use an existing key

The configuration is stored in `~/.oci/config`.

### 4. Create an Object Storage Bucket

The Speech service requires audio files to be in Object Storage:

```bash
# Create a bucket (replace values)
oci os bucket create \
  --compartment-id YOUR_COMPARTMENT_OCID \
  --name speech-audio-bucket
```

Or create via OCI Console: **Storage > Object Storage > Create Bucket**

### 5. Set Up IAM Policies

Ensure your user/group has the following policies:

```
Allow group <your-group> to manage ai-service-speech-family in compartment <compartment-name>
Allow group <your-group> to manage object-family in compartment <compartment-name>
```

## Configuration

Set the following environment variables before running the script:

```bash
export OCI_COMPARTMENT_ID='ocid1.compartment.oc1..aaaaaaa...'
export OCI_NAMESPACE='your-tenancy-namespace'
export OCI_BUCKET_NAME='speech-audio-bucket'
```

### Finding Your Values

| Value | Location |
|-------|----------|
| Compartment OCID | OCI Console > Identity > Compartments > [Your Compartment] |
| Namespace | OCI Console > Object Storage > Bucket Details (or `oci os ns get`) |
| Bucket Name | OCI Console > Object Storage > Buckets |

## Usage

1. Place your audio file in the same directory as the script (default: `New Recording.m4a`)

2. Run the script:
```bash
python speech_to_text.py
```

3. The script will:
   - Upload the audio file to Object Storage
   - Create a transcription job
   - Wait for the job to complete
   - Download and display the transcription
   - Save the result to `transcription_output.txt`

## Supported Audio Formats

OCI Speech service supports:
- WAV
- MP3
- M4A/AAC
- FLAC
- OGG

## Customization

Edit `speech_to_text.py` to change:
- `AUDIO_FILE`: Name of your audio file
- Language: Change `language_code` in `create_transcription_job()` (e.g., `en-US`, `es-ES`, `fr-FR`)

## Troubleshooting

### "Error loading OCI config"
- Ensure `~/.oci/config` exists and is properly formatted
- Run `oci setup config` to reconfigure

### "Bucket not found"
- Create the bucket first: `oci os bucket create -c $OCI_COMPARTMENT_ID --name $OCI_BUCKET_NAME`

### "NotAuthorizedOrNotFound"
- Check IAM policies allow access to Speech service
- Verify compartment OCID is correct
- Ensure Speech service is available in your region

### Transcription job fails
- Check audio file format is supported
- Ensure audio quality is sufficient
- Check OCI Console > Analytics & AI > Speech for job details

## Cost

OCI Speech service pricing:
- Check [OCI Pricing](https://www.oracle.com/cloud/price-list/) for current rates
- First 5,000 minutes/month may be free tier eligible

## License

MIT License
