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

# Используем существующую сеть по ID
data "yandex_vpc_network" "network" {
  network_id = "enps7chdm6i5mjejb51q"
}

# Используем существующую подсеть по ID
data "yandex_vpc_subnet" "subnet" {
  subnet_id = "e9buau810hkqh77fh655"
}

# Получаем данные о существующем снимке диска
data "yandex_compute_snapshot" "adhunt_snapshot" {
  name = "adhunt-disk-ubuntu-20-04"
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
        snapshot_id = data.yandex_compute_snapshot.adhunt_snapshot.id
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
        write_files:
          - path: /etc/systemd/system/adhunt.service
            content: |
              [Unit]
              Description=AdHunt Backend Service
              After=network.target

              [Service]
              User=ubuntu
              WorkingDirectory=/home/ubuntu/AdHunt-backend
              Environment="PATH=/home/ubuntu/AdHunt-backend/venv/bin"
              Environment="PYTHONPATH=/home/ubuntu/AdHunt-backend/AdHunt_backend"
              Environment="DJANGO_SETTINGS_MODULE=AdHunt_backend.settings"
              ExecStart=/home/ubuntu/AdHunt-backend/venv/bin/gunicorn AdHunt_backend.wsgi:application --bind 0.0.0.0:8000 --workers 4 --threads 2 --worker-class gthread --timeout 30 --keep-alive 5 --max-requests 1000 --max-requests-jitter 50
              Restart=always
              RestartSec=10
              StandardOutput=append:/var/log/adhunt/service.log
              StandardError=append:/var/log/adhunt/service.log

              [Install]
              WantedBy=multi-user.target

        runcmd:
          - mkdir -p /var/log/adhunt
          - chown -R ubuntu:ubuntu /var/log/adhunt
          - mkdir -p /home/ubuntu/AdHunt-backend
          - chown -R ubuntu:ubuntu /home/ubuntu/AdHunt-backend
          - mkdir -p /mnt/snapshot
          - mount /dev/vda1 /mnt/snapshot
          - ls -la /mnt/snapshot/home
          - cp -r /mnt/snapshot/home/adhunt/AdHunt-backend/* /home/ubuntu/AdHunt-backend/
          - chown -R ubuntu:ubuntu /home/ubuntu/AdHunt-backend
          - cd /home/ubuntu/AdHunt-backend
          - ls -la /home/ubuntu/AdHunt-backend
          - systemctl daemon-reload
          - systemctl enable adhunt.service
          - systemctl start adhunt.service
          - sleep 5
          - systemctl status adhunt.service
          - journalctl -u adhunt.service --no-pager
      EOT
    }
  }

  scale_policy {
    auto_scale {
      initial_size         = 1
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
    target_group_name = "adhunt-target-group" # создается автоматически
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
    target_group_id = yandex_compute_instance_group.adhunt_group.load_balancer[0].target_group_id

    healthcheck {
      name = "http"
      tcp_options {
        port = 8000
      }
    }
  }
}