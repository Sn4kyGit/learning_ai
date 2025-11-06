#!/usr/bin/env python3
"""
Test Environment Provisioner for CI/CD Integration.

This script provisions and manages test environments for automated testing,
including database setup, service configuration, and environment validation.
"""

import os
import sys
import json
import time
import subprocess
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import argparse
import tempfile
import shutil


@dataclass
class ServiceConfig:
    """Configuration for a test service."""
    name: str
    image: str
    ports: Dict[str, int]
    environment: Dict[str, str]
    health_check: Dict[str, Any]
    ready_timeout: int = 60


@dataclass
class EnvironmentStatus:
    """Status of a test environment component."""
    name: str
    status: str  # "starting", "ready", "failed", "stopped"
    health_check_passed: bool
    start_time: Optional[str] = None
    ready_time: Optional[str] = None
    error_message: Optional[str] = None


class TestEnvironmentProvisioner:
    """Comprehensive test environment provisioning and management."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.environment_id = f"test-env-{int(time.time())}"
        self.services: Dict[str, ServiceConfig] = {}
        self.service_status: Dict[str, EnvironmentStatus] = {}
        self.temp_dir = None
        
        # Define standard test services
        self._define_standard_services()
    
    def log(self, message: str):
        """Log message if verbose mode is enabled."""
        if self.verbose:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
    
    def _define_standard_services(self):
        """Define standard test services configuration."""
        
        # PostgreSQL test database
        self.services["postgres"] = ServiceConfig(
            name="postgres",
            image="postgres:15-alpine",
            ports={"5432": 5432},
            environment={
                "POSTGRES_DB": "businessbot_test",
                "POSTGRES_USER": "postgres",
                "POSTGRES_PASSWORD": "postgres",
                "POSTGRES_HOST_AUTH_METHOD": "trust"
            },
            health_check={
                "test": ["CMD-SHELL", "pg_isready -U postgres -d businessbot_test"],
                "interval": "10s",
                "timeout": "5s",
                "retries": 10,
                "start_period": "30s"
            },
            ready_timeout=120
        )
        
        # Redis cache
        self.services["redis"] = ServiceConfig(
            name="redis",
            image="redis:7-alpine",
            ports={"6379": 6379},
            environment={},
            health_check={
                "test": ["CMD", "redis-cli", "ping"],
                "interval": "10s",
                "timeout": "3s",
                "retries": 10,
                "start_period": "10s"
            },
            ready_timeout=60
        )
        
        # Elasticsearch (for search testing)
        self.services["elasticsearch"] = ServiceConfig(
            name="elasticsearch",
            image="elasticsearch:8.11.0",
            ports={"9200": 9200, "9300": 9300},
            environment={
                "discovery.type": "single-node",
                "xpack.security.enabled": "false",
                "ES_JAVA_OPTS": "-Xms512m -Xmx512m"
            },
            health_check={
                "test": ["CMD-SHELL", "curl -f http://localhost:9200/_cluster/health || exit 1"],
                "interval": "30s",
                "timeout": "10s",
                "retries": 10,
                "start_period": "60s"
            },
            ready_timeout=180
        )
    
    def create_docker_compose_config(self, services: List[str] = None) -> str:
        """Create Docker Compose configuration for test services."""
        if services is None:
            services = ["postgres", "redis"]
        
        self.log(f"Creating Docker Compose config for services: {services}")
        
        compose_config = {
            "version": "3.8",
            "services": {},
            "networks": {
                "test-network": {
                    "driver": "bridge"
                }
            },
            "volumes": {}
        }
        
        for service_name in services:
            if service_name not in self.services:
                self.log(f"Warning: Unknown service {service_name}")
                continue
            
            service = self.services[service_name]
            
            service_config = {
                "image": service.image,
                "environment": service.environment,
                "ports": [f"{host}:{container}" for container, host in service.ports.items()],
                "networks": ["test-network"],
                "healthcheck": service.health_check
            }
            
            # Add service-specific configurations
            if service_name == "postgres":
                service_config["volumes"] = [
                    f"{self.environment_id}_postgres_data:/var/lib/postgresql/data"
                ]
                compose_config["volumes"][f"{self.environment_id}_postgres_data"] = {}
            
            elif service_name == "redis":
                service_config["command"] = ["redis-server", "--appendonly", "yes"]
                service_config["volumes"] = [
                    f"{self.environment_id}_redis_data:/data"
                ]
                compose_config["volumes"][f"{self.environment_id}_redis_data"] = {}
            
            elif service_name == "elasticsearch":
                service_config["volumes"] = [
                    f"{self.environment_id}_es_data:/usr/share/elasticsearch/data"
                ]
                compose_config["volumes"][f"{self.environment_id}_es_data"] = {}
            
            compose_config["services"][service_name] = service_config
        
        return compose_config
    
    def provision_environment(self, services: List[str] = None, use_docker: bool = True) -> Dict[str, Any]:
        """Provision complete test environment."""
        self.log(f"Provisioning test environment: {self.environment_id}")
        
        if services is None:
            services = ["postgres", "redis"]
        
        # Create temporary directory for configuration files
        self.temp_dir = tempfile.mkdtemp(prefix=f"test-env-{self.environment_id}-")
        self.log(f"Using temporary directory: {self.temp_dir}")
        
        provisioning_result = {
            "environment_id": self.environment_id,
            "services": services,
            "provisioning_method": "docker" if use_docker else "local",
            "start_time": datetime.now().isoformat(),
            "status": "provisioning",
            "service_status": {},
            "connection_info": {},
            "temp_directory": self.temp_dir
        }
        
        try:
            if use_docker:
                result = self._provision_with_docker(services)
            else:
                result = self._provision_locally(services)
            
            provisioning_result.update(result)
            provisioning_result["status"] = "ready" if result["success"] else "failed"
            provisioning_result["ready_time"] = datetime.now().isoformat()
            
        except Exception as e:
            self.log(f"Provisioning failed: {e}")
            provisioning_result["status"] = "failed"
            provisioning_result["error"] = str(e)
        
        return provisioning_result
    
    def _provision_with_docker(self, services: List[str]) -> Dict[str, Any]:
        """Provision test environment using Docker Compose."""
        self.log("Provisioning with Docker Compose...")
        
        # Create Docker Compose configuration
        compose_config = self.create_docker_compose_config(services)
        compose_file = Path(self.temp_dir) / "docker-compose.yml"
        
        with open(compose_file, 'w') as f:
            import yaml
            yaml.dump(compose_config, f, default_flow_style=False)
        
        self.log(f"Docker Compose config written to: {compose_file}")
        
        # Start services
        try:
            # Pull images first
            self.log("Pulling Docker images...")
            subprocess.run([
                "docker-compose", "-f", str(compose_file), "pull"
            ], check=True, capture_output=True, text=True)
            
            # Start services
            self.log("Starting services...")
            subprocess.run([
                "docker-compose", "-f", str(compose_file), "up", "-d"
            ], check=True, capture_output=True, text=True)
            
            # Wait for services to be ready
            self.log("Waiting for services to be ready...")
            ready_services = self._wait_for_services_ready(services, compose_file)
            
            # Get connection information
            connection_info = self._get_connection_info(services)
            
            return {
                "success": len(ready_services) == len(services),
                "ready_services": ready_services,
                "failed_services": [s for s in services if s not in ready_services],
                "connection_info": connection_info,
                "compose_file": str(compose_file)
            }
            
        except subprocess.CalledProcessError as e:
            self.log(f"Docker Compose command failed: {e}")
            return {
                "success": False,
                "error": f"Docker Compose failed: {e}",
                "stderr": e.stderr if hasattr(e, 'stderr') else None
            }
    
    def _provision_locally(self, services: List[str]) -> Dict[str, Any]:
        """Provision test environment using local services."""
        self.log("Provisioning with local services...")
        
        # This is a simplified implementation
        # In a real scenario, you would start local services or use existing ones
        
        ready_services = []
        connection_info = {}
        
        for service_name in services:
            if service_name == "postgres":
                # Check if PostgreSQL is available locally
                if self._check_local_postgres():
                    ready_services.append(service_name)
                    connection_info[service_name] = {
                        "host": "localhost",
                        "port": 5432,
                        "database": "businessbot_test",
                        "username": "postgres",
                        "password": "postgres"
                    }
            
            elif service_name == "redis":
                # Check if Redis is available locally
                if self._check_local_redis():
                    ready_services.append(service_name)
                    connection_info[service_name] = {
                        "host": "localhost",
                        "port": 6379,
                        "database": 0
                    }
        
        return {
            "success": len(ready_services) == len(services),
            "ready_services": ready_services,
            "failed_services": [s for s in services if s not in ready_services],
            "connection_info": connection_info
        }
    
    def _wait_for_services_ready(self, services: List[str], compose_file: Path) -> List[str]:
        """Wait for Docker services to be ready."""
        ready_services = []
        
        for service_name in services:
            if service_name not in self.services:
                continue
            
            service = self.services[service_name]
            self.log(f"Waiting for {service_name} to be ready...")
            
            start_time = time.time()
            timeout = service.ready_timeout
            
            while time.time() - start_time < timeout:
                try:
                    # Check service health
                    result = subprocess.run([
                        "docker-compose", "-f", str(compose_file), 
                        "exec", "-T", service_name, "sh", "-c", 
                        " ".join(service.health_check["test"][1:])  # Skip CMD-SHELL
                    ], capture_output=True, text=True, timeout=10)
                    
                    if result.returncode == 0:
                        self.log(f"{service_name} is ready!")
                        ready_services.append(service_name)
                        break
                    
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                    pass
                
                time.sleep(5)
            else:
                self.log(f"{service_name} failed to become ready within {timeout} seconds")
        
        return ready_services
    
    def _check_local_postgres(self) -> bool:
        """Check if local PostgreSQL is available."""
        try:
            result = subprocess.run([
                "pg_isready", "-h", "localhost", "-p", "5432"
            ], capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except:
            return False
    
    def _check_local_redis(self) -> bool:
        """Check if local Redis is available."""
        try:
            result = subprocess.run([
                "redis-cli", "-h", "localhost", "-p", "6379", "ping"
            ], capture_output=True, text=True, timeout=10)
            return "PONG" in result.stdout
        except:
            return False
    
    def _get_connection_info(self, services: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get connection information for provisioned services."""
        connection_info = {}
        
        for service_name in services:
            if service_name not in self.services:
                continue
            
            service = self.services[service_name]
            
            if service_name == "postgres":
                connection_info[service_name] = {
                    "host": "localhost",
                    "port": service.ports["5432"],
                    "database": service.environment["POSTGRES_DB"],
                    "username": service.environment["POSTGRES_USER"],
                    "password": service.environment["POSTGRES_PASSWORD"],
                    "url": f"postgresql://{service.environment['POSTGRES_USER']}:{service.environment['POSTGRES_PASSWORD']}@localhost:{service.ports['5432']}/{service.environment['POSTGRES_DB']}"
                }
            
            elif service_name == "redis":
                connection_info[service_name] = {
                    "host": "localhost",
                    "port": service.ports["6379"],
                    "database": 0,
                    "url": f"redis://localhost:{service.ports['6379']}/0"
                }
            
            elif service_name == "elasticsearch":
                connection_info[service_name] = {
                    "host": "localhost",
                    "port": service.ports["9200"],
                    "url": f"http://localhost:{service.ports['9200']}"
                }
        
        return connection_info
    
    def setup_test_data(self, connection_info: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Set up initial test data in provisioned services."""
        self.log("Setting up test data...")
        
        setup_results = {}
        
        # Setup PostgreSQL test data
        if "postgres" in connection_info:
            setup_results["postgres"] = self._setup_postgres_data(connection_info["postgres"])
        
        # Setup Redis test data
        if "redis" in connection_info:
            setup_results["redis"] = self._setup_redis_data(connection_info["redis"])
        
        return setup_results
    
    def _setup_postgres_data(self, postgres_info: Dict[str, Any]) -> Dict[str, Any]:
        """Set up PostgreSQL test database and schema."""
        try:
            import psycopg2
            
            # Connect to PostgreSQL
            conn = psycopg2.connect(
                host=postgres_info["host"],
                port=postgres_info["port"],
                database=postgres_info["database"],
                user=postgres_info["username"],
                password=postgres_info["password"]
            )
            
            with conn.cursor() as cursor:
                # Create test schema
                cursor.execute("CREATE SCHEMA IF NOT EXISTS test_schema;")
                
                # Create extensions
                cursor.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")
                
                # Create basic test tables (simplified)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS test_organizations (
                        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                        name VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS test_businesses (
                        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                        name VARCHAR(255) NOT NULL,
                        organization_id UUID REFERENCES test_organizations(id),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                # Insert sample data
                cursor.execute("""
                    INSERT INTO test_organizations (name) 
                    VALUES ('Test Organization') 
                    ON CONFLICT DO NOTHING;
                """)
                
                conn.commit()
            
            conn.close()
            
            return {
                "success": True,
                "message": "PostgreSQL test data setup completed"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _setup_redis_data(self, redis_info: Dict[str, Any]) -> Dict[str, Any]:
        """Set up Redis test data."""
        try:
            import redis
            
            # Connect to Redis
            r = redis.Redis(
                host=redis_info["host"],
                port=redis_info["port"],
                db=redis_info["database"]
            )
            
            # Set some test keys
            r.set("test:environment", self.environment_id)
            r.set("test:setup_time", datetime.now().isoformat())
            
            # Create test hash
            r.hset("test:config", mapping={
                "environment": "test",
                "version": "1.0.0",
                "ready": "true"
            })
            
            return {
                "success": True,
                "message": "Redis test data setup completed"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def validate_environment(self, connection_info: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Validate that the test environment is working correctly."""
        self.log("Validating test environment...")
        
        validation_results = {
            "overall_status": "validating",
            "service_validations": {},
            "validation_time": datetime.now().isoformat()
        }
        
        all_valid = True
        
        for service_name, info in connection_info.items():
            self.log(f"Validating {service_name}...")
            
            if service_name == "postgres":
                result = self._validate_postgres(info)
            elif service_name == "redis":
                result = self._validate_redis(info)
            elif service_name == "elasticsearch":
                result = self._validate_elasticsearch(info)
            else:
                result = {"valid": False, "error": f"Unknown service: {service_name}"}
            
            validation_results["service_validations"][service_name] = result
            
            if not result["valid"]:
                all_valid = False
        
        validation_results["overall_status"] = "valid" if all_valid else "invalid"
        return validation_results
    
    def _validate_postgres(self, postgres_info: Dict[str, Any]) -> Dict[str, Any]:
        """Validate PostgreSQL connection and functionality."""
        try:
            import psycopg2
            
            conn = psycopg2.connect(
                host=postgres_info["host"],
                port=postgres_info["port"],
                database=postgres_info["database"],
                user=postgres_info["username"],
                password=postgres_info["password"]
            )
            
            with conn.cursor() as cursor:
                # Test basic query
                cursor.execute("SELECT version();")
                version = cursor.fetchone()[0]
                
                # Test table creation
                cursor.execute("CREATE TEMP TABLE validation_test (id SERIAL PRIMARY KEY, name TEXT);")
                cursor.execute("INSERT INTO validation_test (name) VALUES ('test');")
                cursor.execute("SELECT COUNT(*) FROM validation_test;")
                count = cursor.fetchone()[0]
                
                conn.rollback()  # Clean up temp table
            
            conn.close()
            
            return {
                "valid": True,
                "version": version,
                "test_operations": "passed"
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }
    
    def _validate_redis(self, redis_info: Dict[str, Any]) -> Dict[str, Any]:
        """Validate Redis connection and functionality."""
        try:
            import redis
            
            r = redis.Redis(
                host=redis_info["host"],
                port=redis_info["port"],
                db=redis_info["database"]
            )
            
            # Test basic operations
            test_key = f"validation_test_{int(time.time())}"
            r.set(test_key, "test_value")
            value = r.get(test_key)
            r.delete(test_key)
            
            # Get Redis info
            info = r.info()
            
            return {
                "valid": True,
                "version": info.get("redis_version", "unknown"),
                "test_operations": "passed"
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }
    
    def _validate_elasticsearch(self, es_info: Dict[str, Any]) -> Dict[str, Any]:
        """Validate Elasticsearch connection and functionality."""
        try:
            import requests
            
            # Test cluster health
            response = requests.get(f"{es_info['url']}/_cluster/health", timeout=10)
            response.raise_for_status()
            
            health = response.json()
            
            return {
                "valid": True,
                "cluster_status": health.get("status", "unknown"),
                "test_operations": "passed"
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }
    
    def cleanup_environment(self, provisioning_result: Dict[str, Any]) -> Dict[str, Any]:
        """Clean up provisioned test environment."""
        self.log(f"Cleaning up test environment: {self.environment_id}")
        
        cleanup_result = {
            "environment_id": self.environment_id,
            "cleanup_time": datetime.now().isoformat(),
            "status": "cleaning"
        }
        
        try:
            if provisioning_result.get("provisioning_method") == "docker":
                compose_file = provisioning_result.get("compose_file")
                if compose_file and Path(compose_file).exists():
                    # Stop and remove containers
                    subprocess.run([
                        "docker-compose", "-f", compose_file, "down", "-v"
                    ], capture_output=True, text=True)
                    
                    self.log("Docker containers stopped and removed")
            
            # Clean up temporary directory
            if self.temp_dir and Path(self.temp_dir).exists():
                shutil.rmtree(self.temp_dir)
                self.log(f"Temporary directory cleaned up: {self.temp_dir}")
            
            cleanup_result["status"] = "completed"
            
        except Exception as e:
            self.log(f"Cleanup failed: {e}")
            cleanup_result["status"] = "failed"
            cleanup_result["error"] = str(e)
        
        return cleanup_result


def main():
    """Main entry point for test environment provisioner."""
    parser = argparse.ArgumentParser(description="Test Environment Provisioner for CI/CD")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--services", nargs="+", default=["postgres", "redis"],
                       help="Services to provision")
    parser.add_argument("--method", choices=["docker", "local"], default="docker",
                       help="Provisioning method")
    parser.add_argument("--setup-data", action="store_true", help="Set up test data")
    parser.add_argument("--validate", action="store_true", help="Validate environment")
    parser.add_argument("--cleanup", action="store_true", help="Clean up after provisioning")
    parser.add_argument("--output", default="environment-info.json", 
                       help="Output file for environment information")
    
    args = parser.parse_args()
    
    try:
        provisioner = TestEnvironmentProvisioner(verbose=args.verbose)
        
        # Provision environment
        result = provisioner.provision_environment(
            services=args.services,
            use_docker=(args.method == "docker")
        )
        
        print(f"Environment provisioning: {'SUCCESS' if result.get('success') else 'FAILED'}")
        print(f"Environment ID: {result['environment_id']}")
        
        if result.get("success"):
            print(f"Ready services: {result.get('ready_services', [])}")
            
            # Set up test data if requested
            if args.setup_data:
                setup_result = provisioner.setup_test_data(result.get("connection_info", {}))
                result["setup_data"] = setup_result
                print("Test data setup completed")
            
            # Validate environment if requested
            if args.validate:
                validation_result = provisioner.validate_environment(result.get("connection_info", {}))
                result["validation"] = validation_result
                print(f"Environment validation: {validation_result['overall_status']}")
        
        # Save environment information
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"Environment information saved to: {args.output}")
        
        # Clean up if requested
        if args.cleanup:
            cleanup_result = provisioner.cleanup_environment(result)
            print(f"Environment cleanup: {cleanup_result['status']}")
        
        # Exit with appropriate code
        sys.exit(0 if result.get("success") else 1)
        
    except Exception as e:
        print(f"Environment provisioning failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()