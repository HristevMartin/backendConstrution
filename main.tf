terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
  }
}

variable "project_id" {
  description = "The Google Cloud project ID"
  type        = string
  default     = "stalwart-elixir-458022-d5"
}

variable "region" {
  description = "The Google Cloud region"
  type        = string
  default     = "us-central1"
}


variable "backend_image_name" {
  description = "Backend container image to deploy to Cloud Run"
  type        = string
  default     = "gcr.io/stalwart-elixir-458022-d5/ub-travel-services-run-last:latest"
}


variable "mongodb_uri" {
  description = "MongoDB connection URI"
  type        = string
  default     = "mongodb://10.0.1.2:27017/travelDB"
  sensitive   = false # Can change to false since no credentials
}

variable "secret_key" {
  description = "Secret key for Flask application"
  type        = string
  default     = "super-secure-secret-key-change-this-in-production-12345"
  sensitive   = true
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required services
resource "google_project_service" "cloud_run_api" {
  service            = "run.googleapis.com"
  disable_on_destroy = false
}

# Backend Cloud Run service
resource "google_cloud_run_service" "backend" {
  name     = "ub-travel-services-backend"
  location = var.region

  template {
    spec {
      containers {
        image = var.backend_image_name

        # Your Flask app port
        ports {
          container_port = 8080
        }

        # Environment variables for your Flask app
        env {
          name  = "MONGODB_URI"
          value = var.mongodb_uri
        }

        env {
          name  = "MONGO_DB"
          value = "travelDB"
        }

        env {
          name  = "SECRET_KEY"
          value = var.secret_key
        }

        env {
          name  = "FLASK_ENV"
          value = "production"
        }



        resources {
          limits = {
            cpu    = "1000m"
            memory = "512Mi"
          }
        }
      }
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/maxScale"        = "10"
        "run.googleapis.com/vpc-access-connector" = google_vpc_access_connector.connector.name
        "run.googleapis.com/vpc-access-egress"    = "private-ranges-only"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [
    google_project_service.cloud_run_api,
    google_vpc_access_connector.connector 
  ]
}

# IAM policy to make the backend service accessible
resource "google_cloud_run_service_iam_member" "backend_public_access" {
  service  = google_cloud_run_service.backend.name
  location = google_cloud_run_service.backend.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Output the backend service URL
output "backend_service_url" {
  value = google_cloud_run_service.backend.status[0].url
}

resource "google_compute_firewall" "mongodb_access" {
  name    = "allow-mongodb"
  network = "managementbigcommerce-vpc"

  allow {
    protocol = "tcp"
    ports    = ["27017"]
  }

  # Allow from Cloud Run (or all internal IPs)
  source_ranges = ["10.0.0.0/8"]
  target_tags   = ["mongodb-server"] # tag your VM with this
}


resource "google_project_service" "vpcaccess_api" {
  service            = "vpcaccess.googleapis.com"
  disable_on_destroy = false
}

# VPC Access Connector - allows Cloud Run to reach your VPC
resource "google_vpc_access_connector" "connector" {
  name          = "cloudrun-vpc-connector"
  ip_cidr_range = "172.16.0.0/28" # Choose an unused CIDR range in your VPC
  network       = "managementbigcommerce-vpc"
  region        = var.region

  depends_on = [google_project_service.vpcaccess_api]
}
