*[ACL]: Access-Control List
*[BFD]: Bidirectional Forwarding Detection
*[BGP]: Border Gateway Protocol
*[CHR]: Cloud Hosted Router (MikroTik)
*[CVE]: Common Vulnerabilities and Exposures
*[DERP]: Designated Encrypted Relay for Packets (Tailscale)
*[DTO]: Data Transfer Object — Pydantic request/response models in this codebase, suffixed `*Dto`
*[EOS]: Extensible Operating System (Arista)
*[EULA]: End-User License Agreement
*[EVPN]: Ethernet VPN
*[FB]: Function Block — see Function Block tooltip
*[FRR]: FRRouting
*[GHCR]: GitHub Container Registry
*[gNMI]: gRPC Network Management Interface
*[GLBP]: Gateway Load Balancing Protocol (Cisco)
*[HSRP]: Hot Standby Router Protocol (Cisco)
*[IOL]: IOS On Linux (Cisco)
*[IOS]: Internetwork Operating System (Cisco)
*[IS-IS]: Intermediate System to Intermediate System
*[mTLS]: mutual Transport Layer Security
*[MPLS]: Multi-Protocol Label Switching
*[NIC]: Network Interface Controller
*[NOS]: Network Operating System
*[OSPF]: Open Shortest Path First
*[SR-MPLS]: Segment Routing over MPLS
*[SR Linux]: Service Router Linux (Nokia)
*[SRv6]: Segment Routing over IPv6
*[VRF]: Virtual Routing and Forwarding
*[YANG]: data-modeling language used by gNMI / NETCONF for network device config

[//]: # (Neops platform terms — what they mean across the wider neops ecosystem)
*[Function Block]: A typed Python class implementing one unit of automation work — read configs, push templates, check compliance — orchestrated by the Worker SDK
*[Worker]: A Python process that registers with the workflow engine, polls jobs from the blackboard, executes function blocks, returns results
*[Workflow]: A versioned, declarative YAML description of an ordered sequence of automation operations on network entities
*[Workflow Engine]: The NestJS service that schedules workflows and orchestrates worker execution via the blackboard
*[Blackboard]: The shared job queue between the workflow engine and workers — engine writes jobs, workers read and return results
*[Worker SDK]: neops-worker-sdk-py — the library you import to write function blocks; consumes Remote Lab's `remote_lab_fixture` for tests
*[Remote Lab]: This project — exclusive, queue-brokered access to a real Netlab topology over HTTP
*[LabManager]: The classmethod-only singleton that owns the running lab and enforces one-lab-per-host
*[Netlab]: The upstream lab orchestrator (netlab.tools) this service wraps; manages one topology per host
*[Containerlab]: The container runtime Netlab drives by default in this project (`provider: clab`)
*[Topology]: A single Netlab YAML file declaring nodes, links, modules, and provider
*[Headscale]: Self-hosted, Tailscale-compatible VPN coordination server — the recommended enclosure for the no-auth Remote Lab service
