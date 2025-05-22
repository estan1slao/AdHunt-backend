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

resource "yandex_vpc_network" "network" {
  name = "adhunt-network"
}

resource "yandex_vpc_subnet" "subnet" {
  name           = "adhunt-subnet"
  zone           = "ru-central1-a"
  network_id     = yandex_vpc_network.network.id
  v4_cidr_blocks = ["10.5.0.0/16"]
}

data "yandex_iam_service_account" "sa" {
  name = "adhunt-service-account"
}

resource "yandex_resourcemanager_folder_iam_member" "editor" {
  folder_id = var.folder_id
  role      = "editor"
  member    = "serviceAccount:${yandex_iam_service_account.sa.id}"
}

resource "yandex_resourcemanager_folder_iam_member" "storage_admin" {
  folder_id = var.folder_id
  role      = "storage.admin"
  member    = "serviceAccount:${yandex_iam_service_account.sa.id}"
}

resource "yandex_mdb_postgresql_cluster" "pg" {
  name        = "adhunt-pg"
  environment = "PRODUCTION"
  network_id  = yandex_vpc_network.network.id

  config {
    version = "15"
    resources {
      resource_preset_id = "s2.micro"
      disk_type_id        = "network-ssd"
      disk_size           = 20
    }

    postgresql_config = {
      max_connections = 100
    }
  }

  host {
    zone      = "ru-central1-a"
    subnet_id = yandex_vpc_subnet.subnet.id
  }
}

resource "yandex_mdb_postgresql_user" "user" {
  cluster_id = yandex_mdb_postgresql_cluster.pg.id
  name       = "adhunt_user"
  password   = var.db_password
}

resource "yandex_mdb_postgresql_database" "db" {
  cluster_id = yandex_mdb_postgresql_cluster.pg.id
  name       = "adhunt"
  owner      = yandex_mdb_postgresql_user.user.name
}

resource "yandex_storage_bucket" "bucket" {
  bucket     = "adhunt-static-media"
  access_key = yandex_iam_service_account_static_access_key.sa_keys.access_key
  secret_key = yandex_iam_service_account_static_access_key.sa_keys.secret_key
  acl        = "public-read"
  force_destroy = true
}

resource "yandex_iam_service_account_static_access_key" "sa_keys" {
  service_account_id = yandex_iam_service_account.sa.id
  description        = "Static access keys for S3 usage"
}

resource "yandex_message_queue" "ads_publish_queue" {
  name       = "ads-publish-queue"
  access_key = yandex_iam_service_account_static_access_key.sa_keys.access_key
  secret_key = yandex_iam_service_account_static_access_key.sa_keys.secret_key
}

resource "yandex_resourcemanager_folder_iam_member" "message_writer" {
  folder_id = var.folder_id
  role      = "ymq.writer"
  member    = "serviceAccount:${data.yandex_iam_service_account.sa.id}"
}

resource "yandex_iam_service_account_static_access_key" "sa_keys" {
  service_account_id = data.yandex_iam_service_account.sa.id
  description        = "Static access keys for S3 usage"
}