"""
Zintoo Agentic Inventory Optimizer
Uses LangGraph for multi-step warehouse reallocation reasoning
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Any
from dataclasses import dataclass, asdict
import json

# For LangGraph
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
import operator

from weather_api import CulturalContextAPI

# --- DATA MODELS ---

@dataclass
class ReallocationOrder:
    """Represents a single reallocation decision"""
    order_id: str
    product_id: int
    product_name: str
    source_warehouse: str
    destination_warehouse: str
    quantity: int
    priority: str  # "critical" | "high" | "medium" | "low"
    reason: str
    timestamp: str

class OptimizationState(TypedDict):
    """Agent state for LangGraph"""
    pincode: int
    products_to_check: list
    current_product_idx: int
    demand_data: pd.DataFrame
    inventory_data: pd.DataFrame
    analysis_log: list
    reallocation_orders: list
    alerts: list
    status: str

# --- HELPER FUNCTIONS ---

def load_data(demand_csv: str, inventory_csv: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load and force-type all data columns"""
    df_demand = pd.read_csv(demand_csv)
    df_inventory = pd.read_csv(inventory_csv)
    
    # FORCE TYPES: This prevents the "1 product" filtering bug
    df_demand['pincode'] = df_demand['pincode'].astype(int)
    df_demand['id'] = df_demand['id'].astype(int)
    df_inventory['id'] = df_inventory['id'].astype(int)
    
    return df_demand, df_inventory

def get_pincode_products(df_demand: pd.DataFrame, pincode: int) -> list:
    """Get unique products for a pincode after forcing integer match"""
    target_pincode = int(pincode)
    matched_products = df_demand[df_demand['pincode'] == target_pincode]['id'].unique()
    return matched_products.tolist()

def analyze_product_demand(df_demand: pd.DataFrame, product_id: int, pincode: int, weather_label: str = "Sunny ☀️", event_label: str = "None") -> dict:
    """
    Analyze demand trends for a product with integrated Weather & Indian Festival logic.
    Applies targeted multipliers based on product category matching.
    """
    # 1. Filter data for specific Product + Pincode
    product_data = df_demand[
        (df_demand['id'] == product_id) & 
        (df_demand['pincode'] == pincode)
    ].sort_values('date')
    
    if len(product_data) == 0:
        return None
    
    # 2. Split into Historical and Forecast segments
    forecast_data = product_data[product_data['is_forecast'] == True]
    historical_data = product_data[product_data['is_forecast'] == False]
    
    # 3. Fetch Cultural and Weather Context
    # Note: Import inside function if not done at top to avoid circular imports
    from weather_api import CulturalContextAPI
    ctx = CulturalContextAPI.get_context(weather_label, event_label)
    
    # 4. Calculate Final Multiplier
    # Base weather impact (applies to all products)
    weather_mult = ctx['weather_multiplier']
    
    # Targeted Festival impact (applies only to relevant SKUs)
    festival_mult = 1.0
    product_name = product_data.iloc[0]['name']
    
    if ctx['target_categories']:
        # Check if product name matches any target category (e.g., "White" for Holi)
        if any(cat.lower() in product_name.lower() for cat in ctx['target_categories']):
            festival_mult = ctx['festival_multiplier']
    
    # Combine multipliers (e.g., Rain + Holi surge)
    final_multiplier = weather_mult * festival_mult
    
    # 5. Calculate daily demand with contextual impact
    # We apply the multiplier to the mean and max (peak) forecast values
    forecasted_demand = float(forecast_data['demand'].mean()) * final_multiplier
    peak_demand = float(forecast_data['demand'].max()) * final_multiplier
    
    return {
        'product_id': product_id,
        'product_name': product_name,
        'pincode': pincode,
        'avg_historical_demand': float(historical_data['demand'].mean()),
        'forecasted_demand': forecasted_demand,
        'peak_forecast_demand': peak_demand,
        'context': {
            'weather': weather_label,
            'festival': event_label,
            'total_multiplier': round(final_multiplier, 2),
            'is_targeted_sku': festival_mult > 1.0
        }
    }
def check_inventory_levels(df_inventory: pd.DataFrame, product_id: int, pincode: int) -> dict:
    """Get current inventory across all warehouses for a product"""
    # Map pincode to warehouse logic (simplified)
    pincode_to_warehouse = {
        560001: ['W1 (North BLR)', 'W2 (South BLR)', 'W3 (Central Hub)'],
        560037: ['W2 (South BLR)', 'W3 (Central Hub)', 'W1 (North BLR)'],
        560064: ['W3 (Central Hub)', 'W1 (North BLR)', 'W2 (South BLR)'],
    }
    
    warehouses = pincode_to_warehouse.get(pincode, ['W1 (North BLR)', 'W2 (South BLR)', 'W3 (Central Hub)'])
    inventory_status = {}
    
    for wh in warehouses:
        stock = df_inventory[
            (df_inventory['id'] == product_id) & 
            (df_inventory['warehouse'] == wh)
        ]
        if len(stock) > 0:
            inventory_status[wh] = int(stock.iloc[0]['stock'])
        else:
            inventory_status[wh] = 0
    
    total_stock = sum(inventory_status.values())
    return {
        'product_id': product_id,
        'by_warehouse': inventory_status,
        'total_stock': total_stock,
        'warehouses': warehouses,
    }

def detect_stockout_risk(demand_analysis: dict, inventory_status: dict, safety_margin: int = 2) -> dict:
    """Detect if a pincode will run out of stock"""
    forecasted_demand = demand_analysis['peak_forecast_demand']
    current_stock = inventory_status['total_stock']
    
    risk_level = 'low'
    stock_days_remaining = float('inf')
    
    if forecasted_demand > 0:
        stock_days_remaining = current_stock / forecasted_demand
    
    if current_stock == 0:
        risk_level = 'critical'
    elif stock_days_remaining < safety_margin:
        risk_level = 'critical'
    elif stock_days_remaining < 5:
        risk_level = 'high'
    elif stock_days_remaining < 10:
        risk_level = 'medium'
    
    return {
        'product_id': demand_analysis['product_id'],
        'product_name': demand_analysis['product_name'],
        'risk_level': risk_level,
        'current_stock': current_stock,
        'forecasted_daily_demand': demand_analysis['forecasted_demand'],
        'days_of_stock': stock_days_remaining,
        'needs_reallocation': risk_level in ['critical', 'high'],
    }

def plan_reallocation(risk_analysis: dict, inventory_status: dict, order_counter: list) -> ReallocationOrder | None:
    """Plan a reallocation if needed"""
    if not risk_analysis['needs_reallocation']:
        return None
    
    product_id = risk_analysis['product_id']
    product_name = risk_analysis['product_name']
    current_stock = inventory_status['total_stock']
    forecasted_demand = risk_analysis['forecasted_daily_demand']
    
    # Find warehouse with highest stock
    by_wh = inventory_status['by_warehouse']
    source_wh = max(by_wh.items(), key=lambda x: x[1])[0] if by_wh else None
    
    if not source_wh or by_wh[source_wh] < forecasted_demand * 1.5:
        return None  # Not enough stock even in best warehouse
    
    # Destination is the first warehouse in the priority list (closest to pincode)
    destination_wh = inventory_status['warehouses'][0]
    
    if source_wh == destination_wh:
        return None  # Already in correct warehouse
    
    quantity = int(forecasted_demand * 2.5)  # Safety stock multiplier
    
    order_counter[0] += 1
    order = ReallocationOrder(
        order_id=f"Z-{datetime.now().strftime('%d%H%M')}-{order_counter[0]}",
        product_id=product_id,
        product_name=product_name,
        source_warehouse=source_wh,
        destination_warehouse=destination_wh,
        quantity=quantity,
        priority=risk_analysis['risk_level'],
        reason=f"Prevent stockout: {risk_analysis['days_of_stock']:.1f} days of stock remaining",
        timestamp=datetime.now().isoformat(),
    )
    return order

# --- LANGGRAPH NODES ---

def node_initialize(state: OptimizationState) -> OptimizationState:
    """Initialize agent with pincode and product list"""
    pincode = state['pincode']
    products = get_pincode_products(state['demand_data'], pincode)
    
    state['products_to_check'] = products
    state['current_product_idx'] = 0
    state['analysis_log'] = []
    state['reallocation_orders'] = []
    state['alerts'] = []
    state['status'] = f"Initialized optimization for pincode {pincode}. {len(products)} products to analyze."
    
    return state

def node_analyze_next_product(state: OptimizationState) -> OptimizationState:
    pincode = state['pincode']
    products = state['products_to_check']
    # NEW: Pull weather from the state
    current_weather = state.get('weather_label', "Sunny ☀️")
    current_festival = state.get('event_label', "None")
    
    analysis_log = []
    for p_id in products:
        product_id = int(p_id)
        
        # FIX: Pass the weather_label here!
        demand_analysis = analyze_product_demand(
            state['demand_data'], 
            product_id, 
            pincode, 
            weather_label=current_weather,
            event_label=current_festival
        )
        inventory_status = check_inventory_levels(state['inventory_data'], product_id, pincode)
        
        if demand_analysis:
            log_entry = {
                'product_id': product_id,
                'product_name': demand_analysis['product_name'],
                'demand_analysis': demand_analysis,
                'inventory_status': inventory_status,
            }
            analysis_log.append(log_entry)
    
    return {
        **state,
        "analysis_log": analysis_log,
        "status": f"Analysis complete for {len(analysis_log)} products."
    }
    
    # CRITICAL: Return the ENTIRE list back to the state
    return {
        **state,
        "analysis_log": analysis_log,
        "status": f"Analysis complete for {len(analysis_log)} products."
    }
def node_detect_risks(state: OptimizationState) -> OptimizationState:
    """Detect stockout risks from analysis"""
    for log_entry in state['analysis_log']:
        demand_analysis = log_entry['demand_analysis']
        inventory_status = log_entry['inventory_status']
        
        risk_analysis = detect_stockout_risk(demand_analysis, inventory_status)
        
        if risk_analysis['needs_reallocation']:
            alert = {
                'product_name': risk_analysis['product_name'],
                'risk_level': risk_analysis['risk_level'],
                'current_stock': risk_analysis['current_stock'],
                'days_of_stock': risk_analysis['days_of_stock'],
            }
            state['alerts'].append(alert)
        
        log_entry['risk_analysis'] = risk_analysis
    
    state['status'] = f"Risk detection complete. {len(state['alerts'])} alerts generated."
    return state

def node_plan_reallocations(state: OptimizationState) -> OptimizationState:
    """Plan reallocation orders"""
    order_counter = [0]  # Mutable counter
    
    for log_entry in state['analysis_log']:
        if 'risk_analysis' not in log_entry:
            continue
        
        risk_analysis = log_entry['risk_analysis']
        inventory_status = log_entry['inventory_status']
        
        order = plan_reallocation(risk_analysis, inventory_status, order_counter)
        if order:
            state['reallocation_orders'].append(asdict(order))
    
    state['status'] = f"Reallocation planning complete. {len(state['reallocation_orders'])} orders created."
    return state

def node_summarize(state: OptimizationState) -> OptimizationState:
    """Summarize optimization results"""
    summary = {
        'pincode': state['pincode'],
        'timestamp': datetime.now().isoformat(),
        'products_analyzed': len(state['products_to_check']),
        'alerts_raised': len(state['alerts']),
        'reallocation_orders': len(state['reallocation_orders']),
        'critical_alerts': len([a for a in state['alerts'] if a['risk_level'] == 'critical']),
        'high_alerts': len([a for a in state['alerts'] if a['risk_level'] == 'high']),
    }
    
    state['status'] = (
        f"✅ Optimization Complete | "
        f"Products Analyzed: {summary['products_analyzed']} | "
        f"Alerts: {summary['alerts_raised']} | "
        f"Reallocation Orders: {summary['reallocation_orders']}"
    )
    
    return state

# --- LANGGRAPH WORKFLOW ---

def build_optimization_graph(df_demand: pd.DataFrame, df_inventory: pd.DataFrame):
    """Build the LangGraph workflow"""
    workflow = StateGraph(OptimizationState)
    
    # Add nodes
    workflow.add_node("initialize", node_initialize)
    workflow.add_node("analyze", node_analyze_next_product)
    workflow.add_node("detect_risks", node_detect_risks)
    workflow.add_node("plan_reallocations", node_plan_reallocations)
    workflow.add_node("summarize", node_summarize)
    
    # Add edges (sequential execution)
    workflow.add_edge(START, "initialize")
    workflow.add_edge("initialize", "analyze")
    workflow.add_edge("analyze", "detect_risks")
    workflow.add_edge("detect_risks", "plan_reallocations")
    workflow.add_edge("plan_reallocations", "summarize")
    workflow.add_edge("summarize", END)
    
    return workflow.compile()

def run_optimization(pincode, demand_csv, inventory_csv, weather_label="Sunny ☀️", event_label="None"):
    """Execute the optimization agent"""
    # Load data
    df_demand, df_inventory = load_data(demand_csv, inventory_csv)
    
    # Build graph
    graph = build_optimization_graph(df_demand, df_inventory)
    
    # Initial state
    initial_state = OptimizationState(
        pincode=pincode,
        weather_label=weather_label,
        event_label=event_label,
        products_to_check=[],
        current_product_idx=0,
        demand_data=df_demand,
        inventory_data=df_inventory,
        analysis_log=[],
        reallocation_orders=[],
        alerts=[],
        status="Initializing...",
    )
    
    # Run agent
    result = graph.invoke(initial_state)
    
    return {
        'pincode': result['pincode'],
        'status': result['status'],
        'alerts': result['alerts'],
        'reallocation_orders': result['reallocation_orders'],
        'summary': {
            'products_analyzed': len(result['analysis_log']),
            'alerts_raised': len(result['alerts']),
            'orders_created': len(result['reallocation_orders']),
        },
    }

if __name__ == "__main__":
    # Example usage
    result = run_optimization(
        pincode=560001,
        demand_csv=r"D:\FASHION\data\demand_forecast.csv",
        inventory_csv=r"D:\FASHION\data\warehouse_inventory.csv",
    )
    
    print("\n" + "="*60)
    print("ZINTOO AGENTIC OPTIMIZATION REPORT")
    print("="*60)
    print(f"Pincode: {result['pincode']}")
    print(f"Status: {result['status']}")
    print(f"\nSummary:")
    print(f"  Products Analyzed: {result['summary']['products_analyzed']}")
    print(f"  Alerts Raised: {result['summary']['alerts_raised']}")
    print(f"  Reallocation Orders: {result['summary']['orders_created']}")
    
    if result['alerts']:
        print(f"\n⚠️  ALERTS ({len(result['alerts'])}):")
        for alert in result['alerts'][:5]:  # Show first 5
            print(f"  - {alert['product_name']} ({alert['risk_level'].upper()}): "
                  f"{alert['days_of_stock']:.1f} days of stock")
    
    if result['reallocation_orders']:
        print(f"\n📦 REALLOCATION ORDERS ({len(result['reallocation_orders'])}):")
        for order in result['reallocation_orders'][:3]:  # Show first 3
            print(f"  - Order {order['order_id']}: {order['quantity']} units")
            print(f"    {order['source_warehouse']} → {order['destination_warehouse']}")
            print(f"    Priority: {order['priority'].upper()} | {order['reason']}")
