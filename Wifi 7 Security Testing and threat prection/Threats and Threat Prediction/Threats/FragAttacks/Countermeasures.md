• To Prevent Aggregation Attacks: Wi-Fi stations must either stop using frame aggregation (A-MSDU) or ensure that the aggregation flag is always authenticated (by using SPP A-MSDUs).  

• To Prevent Fragmentation Attacks: Receivers must be updated to:
	• Verify that all fragments of a reassembled frame were encrypted under the same session key.  
	• Clear the fragment cache (remove incomplete fragments) whenever a device re-connects to a network or changes its security context.