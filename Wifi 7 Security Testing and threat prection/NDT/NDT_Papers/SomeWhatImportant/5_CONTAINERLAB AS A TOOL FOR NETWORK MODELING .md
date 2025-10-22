# **CONTAINERLAB AS A TOOL FOR NETWORK MODELING AND SIMULATION BASED ON CONTAINERIZATION**

_Serhii Shestopalov_  
Kharkiv National University of Radioelectronics,  
Department of Infocommunication Engineering named after V.V. Popovsky, Ukraine  
📧 Email: [serhii.shestopalov@nure.ua](mailto:serhii.shestopalov@nure.ua)

---

## **Abstract**

In the last decade, containerization technologies such as Docker have advanced rapidly, enabling isolated execution of multiple operating environments without the need for full hardware emulation. Compared to traditional virtual machines, this approach offers greater standardization, scalability, and automated deployment while consuming fewer resources.  
**Containerlab** addresses the problem of deploying and interconnecting containers for complex network topologies. It is an open-source command-line tool that simplifies the creation of container- and VM-based network laboratories. Using simple YAML configuration files, it automates the creation and configuration of network links between nodes and manages their lifecycle.  
This paper reviews Containerlab’s main features and highlights its applications in **development**, **testing**, **education**, **security auditing**, and **network automation**.

---

## **1. Introduction**

The last decade has witnessed a rapid rise in containerization technologies, beginning with the release of **Docker (2013)**. Containerization allows the execution of **isolated operating environments** without complete hardware virtualization. These environments appear as fully functional separate computers to the software running inside them.

Unlike traditional virtual machines (VMs), containers:

- consume significantly fewer resources,
    
- provide standardization and scalability,
    
- support automated deployment of applications in isolated environments, and
    
- efficiently share host system resources such as CPU, storage, and network interfaces.
    

As a result, organizations can build more complex systems and achieve better hardware utilization

CONTAINERLAB ЯК ІНСТУРМЕНТ

.

---

## **2. From Application Containers to Network Operating Systems**

Initially, containerization was mainly used for web servers and user applications. However, as the technology matured, **Network Operating Systems (NOS)** emerged that support container execution, such as:

- **Nokia SR Linux**,
    
- **Arista cEOS**,
    
- **Azure SONiC**,
    
- **Juniper cRPD**,
    
- **FRRouting (FRR)**.
    

These systems enable network engineers to emulate routers, switches, and other devices in containerized environments for design and testing purposes.

---

## **3. The Challenge: Network Interconnection Between Containers**

While tools like **Docker Compose** can orchestrate multiple containers, they lack capabilities to:

- create **peer-to-peer (P2P)** links, and
    
- model **complex multi-node network topologies**.
    

This limitation hinders their use for realistic network simulation.  
To solve this problem, **Containerlab** was created — an **open-source CLI tool** that simplifies the deployment of network labs based on containers and VMs.

Containerlab uses **YAML topology files** to describe networks, automates the setup of virtual links, and manages node lifecycles

CONTAINERLAB ЯК ІНСТУРМЕНТ

.

---

## **4. Main Features and Capabilities of Containerlab**

1. **Wide NOS support:**  
    Compatible with **Nokia SR Linux**, **Arista cEOS**, **FRRouting (FRR)**, and others, enabling realistic network emulation with multiple vendors and protocols
    
    CONTAINERLAB ЯК ІНСТУРМЕНТ
    
    .
    
2. **Topology definition with YAML files:**  
    Network nodes and connections can be easily defined using human-readable YAML files, allowing repeatable and transparent creation of complex networks
    
    CONTAINERLAB ЯК ІНСТУРМЕНТ
    
    .
    
3. **Automatic interface and link creation:**  
    Containerlab leverages Linux mechanisms such as **veth** (virtual Ethernet pairs) and **bridge** to build high-performance, low-latency connections between nodes
    
    CONTAINERLAB ЯК ІНСТУРМЕНТ
    
    .
    
4. **Lifecycle management:**  
    Provides commands to deploy, stop, and destroy topologies — making lab management simple and fast
    
    CONTAINERLAB ЯК ІНСТУРМЕНТ
    
    .
    
5. **Integration with VRnetlab:**  
    For network operating systems that cannot run directly in containers, Containerlab integrates with **VRnetlab**, allowing virtual routers to operate within Docker containers
    
    CONTAINERLAB ЯК ІНСТУРМЕНТ
    
    .
    
6. **CI/CD pipeline integration:**  
    Supports **Continuous Integration and Continuous Delivery (CI/CD)** processes, enabling automated testing and validation of network configurations
    
    CONTAINERLAB ЯК ІНСТУРМЕНТ
    
    .
    
7. **Scalability and resource efficiency:**  
    Containers consume less overhead than VMs, allowing the simulation of larger topologies on a single host
    
    CONTAINERLAB ЯК ІНСТУРМЕНТ
    
    .
    

---

## **5. Applications of Containerlab**

Containerlab can be used in multiple fields:

- **Rapid development and testing:**  
    Build temporary test environments for new configurations, network services, and protocols.
    
- **Education and training:**  
    Teachers and students can simulate realistic topologies for learning networking concepts hands-on.
    
- **Security auditing and monitoring:**  
    Security experts can replicate networks to simulate **cyberattacks**, analyze vulnerabilities, and test defense mechanisms.
    
- **Automation and orchestration:**  
    Integrates with tools such as **Ansible** for automated configuration and management of network devices
    
    CONTAINERLAB ЯК ІНСТУРМЕНТ
    
    .
    

---

## **6. Conclusion**

Containerlab is a **powerful and accessible** tool for **network modeling and simulation**, utilizing the latest containerization technologies.  
It simplifies the process of building, configuring, and managing virtual network labs, making it ideal for engineers, researchers, and educators.

Being **open-source and free**, Containerlab encourages innovation and experimentation, fostering modern network design, testing, and education.

---

## **References**

1. Docker Inc. _What is a Container?_  
    [https://www.docker.com/resources/what-container](https://www.docker.com/resources/what-container)
    
2. Containerlab Project. _Containerlab Documentation._  
    [https://containerlab.dev/](https://containerlab.dev/)
    
3. Containerlab Project. _Supported Nodes._  
    [https://containerlab.dev/manual/kinds/](https://containerlab.dev/manual/kinds/)
    
4. Containerlab Project. _Topology Definition._  
    [https://containerlab.dev/manual/topo-def-file/](https://containerlab.dev/manual/topo-def-file/)
    
5. Containerlab Project. _Network Wiring Concepts._  
    [https://containerlab.dev/manual/network/](https://containerlab.dev/manual/network/)
    
6. Containerlab Project. _CLI Reference._  
    [https://containerlab.dev/cmd/deploy/](https://containerlab.dev/cmd/deploy/)
    
7. VRnetlab Project. _VRnetlab GitHub Repository._  
    [https://github.com/hellt/vrnetlab](https://github.com/hellt/vrnetlab)
    
8. Containerlab Project. _CI/CD Integration._  
    [https://containerlab.dev/manual/ci-cd/](https://containerlab.dev/manual/ci-cd/)
    
9. Containerlab Project. _Performance and Scaling._  
    [https://containerlab.dev/manual/performance/](https://containerlab.dev/manual/performance/)