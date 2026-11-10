variable "env" {
  description = "Environment name (dev or prod)."
  type        = string
  validation {
    condition     = contains(["dev", "prod"], var.env)
    error_message = "env must be dev or prod."
  }
}

variable "location" {
  description = "Azure region."
  type        = string
  default     = "eastus2"
}

variable "prefix" {
  description = "Short lowercase name prefix (3-10 letters or digits)."
  type        = string
  default     = "aiops"
  validation {
    condition     = can(regex("^[a-z0-9]{3,10}$", var.prefix))
    error_message = "prefix must be 3-10 lowercase letters or digits."
  }
}

variable "log_retention_days" {
  description = "Log Analytics retention."
  type        = number
  default     = 30
}

variable "tags" {
  description = "Tags on every resource."
  type        = map(string)
  default = {
    workload = "aiops-triage"
    owner    = "ops-platform"
    data     = "synthetic"
  }
}

variable "vm_size" {
  description = "Cluster VM size (CPU only)."
  type        = string
  default     = "Standard_D8s_v5"
}

variable "max_nodes" {
  description = "Most nodes the cluster may scale to (it idles at 0)."
  type        = number
  default     = 1
  validation {
    condition     = var.max_nodes >= 1 && var.max_nodes <= 2
    error_message = "max_nodes must be 1 or 2."
  }
}
