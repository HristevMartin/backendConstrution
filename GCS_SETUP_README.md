# Google Cloud Storage Setup for Profile Images

This project now uses Google Cloud Storage (GCS) for storing profile images instead of local file storage.

## Prerequisites

1. **Google Cloud Project**: You need a Google Cloud Platform project with billing enabled.
2. **Cloud Storage API**: Enable the Cloud Storage API in your GCP project.
3. **Service Account**: Create a service account with Storage Admin or Storage Object Admin permissions.

## Setup Instructions

### 1. Create a GCS Bucket

```bash
# Using gcloud CLI
gcloud storage buckets create gs://profile_images --location=US

# Or create through the Google Cloud Console
```

### 2. Set up Authentication

**Option A: Service Account Key (Development)**
1. Go to the Google Cloud Console
2. Navigate to IAM & Admin > Service Accounts
3. Create a new service account or use an existing one
4. Download the JSON key file
5. Set the path in your environment variables

**Option B: Application Default Credentials (Production)**
- Use Google Application Default Credentials for cloud environments
- No key file needed when running on Google Cloud Platform

### 3. Environment Variables

Create a `.env` file or set these environment variables:

```bash
# Google Cloud Storage Configuration
GCS_BUCKET_NAME=profile_images
GCS_PROJECT_ID=your-gcp-project-id
GCS_CREDENTIALS_PATH=path/to/your/service-account-key.json

# Database Configuration
MONGODB_URI=mongodb://localhost:27017/travelDB
SECRET_KEY=your-secret-key-here
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

## File Organization Structure

The files will be organized in GCS as follows:

```
profile_images/                    # Bucket name
├── profile_image_pictures/        # Profile photos folder
│   ├── user_123/                  # User ID folder
│   │   ├── photo1_20240101_120000.jpg
│   │   └── photo2_20240102_130000.png
│   └── user_456/
│       └── avatar_20240103_140000.jpg
└── profile_project_pictures/      # Project photos folder (future use)
    ├── user_123/
    └── user_456/
```

## Security Considerations

1. **Public vs Private**: Currently, uploaded files are made publicly accessible. For sensitive data, consider:
   - Removing the `blob.make_public()` call
   - Using signed URLs for temporary access
   - Implementing proper authentication

2. **File Validation**: The current implementation includes basic file validation. Consider adding:
   - File size limits
   - File type restrictions
   - Virus scanning

3. **Permissions**: Use the principle of least privilege for service account permissions.

## Usage

The `TraderForm` resource now automatically uploads profile images to GCS. The database stores the public URL of the uploaded file instead of a local file path.

### GCSHandler Methods

- `upload_profile_image(file, user_id, file_type)`: Upload a file to GCS
- `delete_file(file_url)`: Delete a file using its URL
- `get_signed_url(blob_path, expiration_minutes)`: Generate signed URLs for private access
- `list_user_files(user_id, file_type)`: List all files for a user

## Troubleshooting

1. **Authentication Errors**: Ensure your service account has proper permissions and the credentials path is correct.
2. **Bucket Not Found**: Make sure the bucket exists and the name matches your configuration.
3. **Upload Failures**: Check your internet connection and GCP quotas.

## Migration from Local Storage

If you have existing local files, you'll need to migrate them to GCS. The old files in the `uploads/` directory can be safely removed after migration. 