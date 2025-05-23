terraform {
  required_providers {
    yandex = {
      source  = "yandex-cloud/yandex"
      version = ">= 0.89"
    }
  }
}

provider "yandex" {
  token     = var.yc_token
  cloud_id  = var.cloud_id
  folder_id = var.folder_id
  zone      = "ru-central1-a"
}

data "yandex_vpc_network" "network" {
  name = "adhunt-network" 
}

data "yandex_vpc_subnet" "subnet" {
  name = "adhunt-subnet"
}

# Создание образа из существующей ВМ
resource "yandex_compute_image" "adhunt_image" {
  name       = "adhunt-image"
  source_disk_id = "existing-vm-disk-id"  # Замените на ID диска существующей ВМ
}

resource "yandex_lb_target_group" "adhunt_target_group" {
  name = "adhunt-target-group"
}

# Создание группы экземпляров
resource "yandex_compute_instance_group" "adhunt_group" {
  name               = "adhunt-instance-group"
  folder_id          = var.folder_id
  service_account_id = var.service_account_id

  instance_template {
    platform_id = "standard-v1"

    resources {
      cores  = 2
      memory = 4
    }

    boot_disk {
      initialize_params {
        image_id = yandex_compute_image.adhunt_image.id
      }
    }

    network_interface {
      network_id = data.yandex_vpc_network.network.id
      subnet_ids = [data.yandex_vpc_subnet.subnet.id]
      nat        = true
    }

    metadata = {
      user-data = <<-EOT
        #cloud-config
        runcmd:
          - cd ~/AdHunt-backend
          - source venv/bin/activate
          - PYTHONPATH=./AdHunt_backend DJANGO_SETTINGS_MODULE=AdHunt_backend.settings gunicorn AdHunt_backend.wsgi:application --bind 0.0.0.0:8000
      EOT
    }
  }

  scale_policy {
    auto_scale {
      min_zone_size        = 1
      max_size             = 4
      measurement_duration = 60
      warmup_duration      = 60
      stabilization_duration = 120
      cpu_utilization_target = 60
    }
  }

  deploy_policy {
    max_unavailable = 1
    max_expansion   = 1
  }

  allocation_policy {
    zones = ["ru-central1-a"]
  }

  health_check {
    tcp_options {
      port = 8000
    }
  }

  load_balancer {
    target_group_id = yandex_lb_target_group.adhunt_target_group.id
  }
}

# Создание балансировщика нагрузки
resource "yandex_lb_network_load_balancer" "adhunt_nlb" {
  name = "adhunt-nlb"

  listener {
    name        = "adhunt-listener"
    port        = 80
    target_port = 8000
    protocol    = "tcp"
  }

  attached_target_group {
    target_group_id = yandex_lb_target_group.adhunt_target_group.id

    healthcheck {
      name = "http"
      tcp_options {
        port = 8000
      }
    }
  }
}