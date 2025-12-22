variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "asia-southeast1"
}

variable "cluster_name" {
  description = "GKE cluster name"
  type        = string
  default     = "rag-chatbot-gke"
}

variable "node_count" {
  description = "Desired node count"
  type        = number
  default     = 2
}

variable "node_pool_min" {
  description = "Autoscaler min nodes"
  type        = number
  default     = 1
}

variable "node_pool_max" {
  description = "Autoscaler max nodes"
  type        = number
  default     = 4
}

variable "machine_type" {
  description = "Node machine type"
  type        = string
  default     = "e2-standard-4"
}

variable "environment" {
  description = "Environment label"
  type        = string
  default     = "dev"
}

# GPU node pool configuration
variable "gpu_node_count" {
  description = "Initial GPU node count"
  type        = number
  default     = 1
}

variable "gpu_node_pool_min" {
  description = "GPU node pool minimum (preemptible for cost)"
  type        = number
  default     = 0
}

variable "gpu_node_pool_max" {
  description = "GPU node pool maximum"
  type        = number
  default     = 3
}

variable "gpu_machine_type" {
  description = "GPU node machine type (g2-standard-4 for L4, a2-highgpu-1g for A100)"
  type        = string
  default     = "g2-standard-4"  # 4 vCPU, 16GB RAM, 1x L4 GPU
}

variable "gpu_count" {
  description = "Number of GPUs per node (L4 supports 1-4)"
  type        = number
  default     = 1
}
