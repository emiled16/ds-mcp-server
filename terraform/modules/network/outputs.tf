output "network_id" { value = google_compute_network.vpc.id }
output "subnet_id" { value = google_compute_subnetwork.subnet.id }
output "subnet_name" { value = google_compute_subnetwork.subnet.name }
output "private_vpc_connection_id" { value = google_service_networking_connection.private_vpc_connection.id }
