==Flaw 1: Frame Aggregation Attack (CVE-2020-24588)==

• The Wi-Fi Feature (A-MSDU): To improve efficiency, Wi-Fi uses Frame Aggregation (specifically, Aggregate MAC Service Data Units or A-MSDU) to bundle multiple small network packets into a single, larger Wi-Fi frame. A specific flag in the frame header tells the receiver to process the payload as a bundle of aggregated packets.  
• The Flaw: By default, the flag that signals A-MSDU aggregation is not authenticated.  
• The Attack:
1. An attacker intercepts a normal, non-aggregated encrypted frame.
2. The attacker, positioned as a Man-in-the-Middle (MitM), flips the unauthenticated A-MSDU flag on the intercepted frame.  
3. The victim device receives the frame and, seeing the flag set, mistakenly interprets the frame's content as a collection of smaller, aggregated packets.  
4. By carefully crafting the original packet's data (e.g., an IPv4 packet), the attacker can manipulate how the victim parses the frame, causing it to see a forged, malicious network packet (such as a DNS server update) inside the payload.  
• Impact: This injection attack can be used to redirect a victim's traffic. For example, the attacker can inject a malicious DNS server address (using an ICMPv6 Router Advertisement), allowing them to intercept or redirect all of the victim's traffic.  

==Flaw 2: Mixed Key Fragmentation Attack (CVE-2020-24587)==

• The Wi-Fi Feature: Frame Fragmentation splits a large Wi-Fi frame into smaller pieces, or fragments, to increase reliability, as only the lost fragments need to be retransmitted. All fragments of a single frame should be encrypted under the same session key.  
• The Flaw: The 802.11 standard does not require the receiver to verify that all fragments of a reassembled frame were decrypted using the same pairwise session key.  
• The Attack (Exfiltration):
5. Preparation (Key k): The attacker forces the victim to send a large, fragmented packet addressed to the attacker's server. The attacker intercepts this and only forwards the first fragment to the Access Point (AP). The AP decrypts and stores this incomplete fragment (part of a packet destined for the attacker).  
6. Key Update: The Wi-Fi network then updates the session key from k to a new key l (called rekeying).  
7. Exploitation (Key l): The victim sends a new packet containing sensitive data (e.g., a username/password), which is also fragmented using the new key l.  
8. The attacker intercepts this sensitive fragmented packet and forwards only the second fragment of the sensitive packet to the AP.  
9. The vulnerable AP combines the first fragment (stored from key k) with the second fragment (received with key l and containing sensitive data) to reassemble a completely forged packet. Since the header of the first fragment is used, the final packet is now addressed to the attacker's server, thus exfiltrating the victim's sensitive data.  
• Affects: WEP, CCMP, and GCMP.  

==Flaw 3: Fragment Cache Poisoning==

• The Flaw: The 802.11 standard does not require devices to clear (or flush) their memory (the fragment cache) of any incomplete, partially received fragments when the device connects to a different Wi-Fi network or updates its security context.  
• The Attack:
10. The attacker first injects a malicious fragment into the victim's fragment cache (while the victim is connected to the attacker's network or a vulnerable hotspot).  
11. The victim then connects to a legitimate target Wi-Fi network.
12. The attacker sends a final, legitimate fragment on the target network.
13. The victim's device combines the malicious fragment from its cache with the final legitimate fragment, reassembling a complete, malicious packet and allowing the attacker to inject arbitrary packets.  
14. Widespread Implementation Flaws
In addition to the fundamental design flaws, the researchers found multiple widespread implementation vulnerabilities that make attacks even easier.  
• The most common flaw is that many receivers do not check if all fragments belong to the same frame. This allows an attacker to trivially forge frames by mixing fragments from any two different frames.  
• Other flaws allow attackers to mix encrypted and plaintext fragments or inject plaintext aggregated frames.