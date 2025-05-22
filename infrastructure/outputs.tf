output "database_url" {
  value = "postgres://${yandex_mdb_postgresql_user.user.name}:${var.db_password}@${yandex_mdb_postgresql_cluster.pg.host[0].fqdn}:6432/${yandex_mdb_postgresql_database.db.name}"
  sensitive = true
}

output "s3_bucket_name" {
  value = yandex_storage_bucket.bucket.bucket
}

output "s3_endpoint_url" {
  value = "https://storage.yandexcloud.net"
}
