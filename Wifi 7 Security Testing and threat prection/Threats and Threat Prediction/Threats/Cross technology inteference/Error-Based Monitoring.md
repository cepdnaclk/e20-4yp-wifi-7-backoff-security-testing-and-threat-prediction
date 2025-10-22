### **Receiver Error Tracking**

- Implemented on a **Broadcom BCM4318 WiFi card**, which tracks 8 types of receiver events (Bad PLCP, Bad FCS, Invalid MAC Header, etc.).
    
- Errors are sampled every **250 µs**, forming a **time-slotted event vector**.
    
- **Error bursts** correspond to interference events, delimited using the receiver’s “busy time” register.
    

### **Observed Error Patterns**

- **ZigBee**: Regular short bursts (~1 ms apart).
    
- **Microwave**: Errors appear mainly at start and end of 10 ms radiation cycles.
    
- **LTE-U**: Similar to ZigBee but denser; first error often delayed relative to channel activation.
    

These **temporal and statistical differences** in error patterns enable discrimination between interference types
