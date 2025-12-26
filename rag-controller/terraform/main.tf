terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.22"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

data "google_client_config" "default" {}

data "google_project" "project" {}

resource "google_container_cluster" "rag" {
  name     = var.cluster_name
  location = var.region

  remove_default_node_pool = true
  initial_node_count       = 1

  networking_mode = "VPC_NATIVE"
  ip_allocation_policy {}

  release_channel {
    channel = "REGULAR"
  }

  master_auth {
    client_certificate_config {
      issue_client_certificate = false
    }
  }
}

# Primary CPU node pool - already created by complete_setup.sh
# Commented out to avoid conflicts with existing infrastructure
# resource "google_container_node_pool" "primary" {
#   name       = "primary"
#   location   = var.region
#   cluster    = google_container_cluster.rag.name
#   node_count = var.node_count
#
#   node_config {
#     machine_type = var.machine_type
#     oauth_scopes = [
#       "https://www.googleapis.com/auth/cloud-platform",
#     ]
#     labels = {
#       env = var.environment
#     }
#     tags = ["rag-chatbot"]
#     metadata = {
#       disable-legacy-endpoints = "true"
#     }
#   }
#
#   autoscaling {
#     min_node_count = var.node_pool_min
#     max_node_count = var.node_pool_max
#   }
# }

# GPU-accelerated node pool for embedding inference
resource "google_container_node_pool" "gpu" {
  name       = "gpu-pool"
  location   = var.region
  cluster    = google_container_cluster.rag.name
  node_count = var.gpu_node_count

  node_config {
    machine_type       = var.gpu_machine_type
    preemptible        = true  # ~70% cost reduction
    disk_size_gb       = 30  # Reduced to avoid quota limits

    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform",
    ]

    labels = {
      env              = var.environment
      workload         = "gpu"
      accelerator_type = "nvidia-l4"
    }

    tags = ["rag-chatbot", "gpu"]

    metadata = {
      disable-legacy-endpoints = "true"
    }

    # NVIDIA GPU drivers auto-installed by GKE
    guest_accelerator {
      type  = "nvidia-l4"
      count = var.gpu_count
    }

    # Taints to ensure only GPU workloads use these nodes
    taint {
      key    = "accelerator"
      value  = "gpu"
      effect = "NO_SCHEDULE"
    }
  }

  autoscaling {
    min_node_count = var.gpu_node_pool_min
    max_node_count = var.gpu_node_pool_max
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }
}

output "kubeconfig" {
  description = "gcloud command to fetch kubeconfig"
  value       = "gcloud container clusters get-credentials ${google_container_cluster.rag.name} --region ${var.region} --project ${var.project_id}"
}
