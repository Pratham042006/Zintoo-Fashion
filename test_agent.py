"""
Test script for Zintoo Agentic Optimizer
Run this to verify the agent logic before integrating into Streamlit
"""

import sys
sys.path.insert(0, r"D:\FASHION")

from agent_optimizer import run_optimization
import json
from datetime import datetime

def print_header(text):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)

def test_single_pincode(pincode: int):
    """Test optimization for a single pincode"""
    print_header(f"Testing Pincode: {pincode}")
    
    result = run_optimization(
        pincode=pincode,
        demand_csv=r"D:\FASHION\data\demand_forecast.csv",
        inventory_csv=r"D:\FASHION\data\warehouse_inventory.csv",
    )
    
    print(f"\n✅ Status: {result['status']}")
    print(f"\nSummary:")
    print(f"  📊 Products Analyzed: {result['summary']['products_analyzed']}")
    print(f"  ⚠️  Alerts Raised: {result['summary']['alerts_raised']}")
    print(f"  📦 Reallocation Orders: {result['summary']['orders_created']}")
    
    # Display Alerts
    if result['alerts']:
        print(f"\n⚠️  TOP ALERTS ({len(result['alerts'])}):")
        print("-" * 70)
        for i, alert in enumerate(result['alerts'][:5], 1):
            print(f"{i}. {alert['product_name']}")
            print(f"   Risk Level: {alert['risk_level'].upper()}")
            print(f"   Current Stock: {alert['current_stock']} units")
            print(f"   Days of Stock: {alert['days_of_stock']:.2f} days")
            print()
    
    # Display Reallocation Orders
    if result['reallocation_orders']:
        print(f"\n📦 REALLOCATION ORDERS ({len(result['reallocation_orders'])}):")
        print("-" * 70)
        for i, order in enumerate(result['reallocation_orders'][:5], 1):
            print(f"{i}. Order {order['order_id']}")
            print(f"   Product: {order['product_name']}")
            print(f"   Quantity: {order['quantity']} units")
            print(f"   Route: {order['source_warehouse']} → {order['destination_warehouse']}")
            print(f"   Priority: {order['priority'].upper()}")
            print(f"   Reason: {order['reason']}")
            print()
    
    return result

def test_all_pincodes():
    """Test all pincodes in the system"""
    print_header("TESTING ALL PINCODES")
    
    pincodes = [560001, 560037, 560064]
    all_results = {}
    
    for pincode in pincodes:
        result = test_single_pincode(pincode)
        all_results[pincode] = result
    
    # Summary
    print_header("OVERALL SUMMARY")
    total_alerts = sum(r['summary']['alerts_raised'] for r in all_results.values())
    total_orders = sum(r['summary']['orders_created'] for r in all_results.values())
    
    print(f"\nAcross {len(pincodes)} pincodes:")
    print(f"  📊 Total Products Analyzed: {sum(r['summary']['products_analyzed'] for r in all_results.values())}")
    print(f"  ⚠️  Total Alerts: {total_alerts}")
    print(f"  📦 Total Orders: {total_orders}")
    
    for pincode, result in all_results.items():
        print(f"\n  Pincode {pincode}:")
        print(f"    - Alerts: {result['summary']['alerts_raised']}")
        print(f"    - Orders: {result['summary']['orders_created']}")

if __name__ == "__main__":
    print("\n🚀 ZINTOO AGENTIC OPTIMIZER - TEST SUITE\n")
    
    # Option 1: Test single pincode
    print("Running single pincode test (560001)...")
    single_result = test_single_pincode(560001)
    
    # Option 2: Uncomment to test all pincodes
    # test_all_pincodes()
    
    print("\n✅ Test complete!")
