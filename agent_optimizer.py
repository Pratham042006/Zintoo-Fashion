"""
Zintoo Agentic Inventory Optimizer - COMPLETE WORKING VERSION
Weather and Event multipliers FULLY INTEGRATED AND APPLIED
"""

import pandas as pd
import numpy as np
from datetime import datetime
from dataclasses import dataclass, asdict
from langgraph.graph import StateGraph, START, END
from typing import TypedDict

from weather_api import CulturalContextAPI

# === MODELS ===

@dataclass
class ReallocationOrder:
    order_id: str
    product_id: int
    product_name: str
    source_warehouse: str
    destination_warehouse: str
    quantity: int
    priority: str
    reason: str
    weather_multiplier: float
    timestamp: str

class OptimizationState(TypedDict):
    pincode: int
    weather_label: str
    event_label: str
    products_to_check: list
    demand_data: pd.DataFrame
    inventory_data: pd.DataFrame
    analysis_log: list
    reallocation_orders: list
    alerts: list
    status: str

# === HELPERS ===

def load_data(demand_csv, inventory_csv):
    df_d = pd.read_csv(demand_csv)
    df_i = pd.read_csv(inventory_csv)
    df_d['pincode'] = df_d['pincode'].astype(int)
    df_d['id'] = df_d['id'].astype(int)
    df_i['id'] = df_i['id'].astype(int)
    return df_d, df_i

def get_products(df_demand, pincode):
    return df_demand[df_demand['pincode'] == int(pincode)]['id'].unique().tolist()

def analyze_demand(df_demand, product_id, pincode, weather_label, event_label):
    """MULTIPLIER CALCULATION HAPPENS HERE"""
    product_data = df_demand[
        (df_demand['id'] == product_id) & 
        (df_demand['pincode'] == pincode)
    ]
    
    if len(product_data) == 0:
        return None
    
    # ✅ GET CONTEXT FROM WEATHER API
    ctx = CulturalContextAPI.get_context(weather_label, event_label)
    
    # ✅ CALCULATE COMBINED MULTIPLIER
    weather_mult = ctx['weather_multiplier']
    festival_mult = 1.0
    
    product_name = product_data.iloc[0]['name']
    if ctx['target_categories']:
        if any(cat.lower() in product_name.lower() for cat in ctx['target_categories']):
            festival_mult = ctx['festival_multiplier']
    
    combined_mult = weather_mult * festival_mult
    
    # ✅ APPLY MULTIPLIER TO FORECAST
    forecast_data = product_data[product_data['is_forecast'] == True]
    hist_data = product_data[product_data['is_forecast'] == False]
    
    if not forecast_data.empty:
        adjusted_forecast = forecast_data['demand'].values * combined_mult
    else:
        adjusted_forecast = np.array([])
    
    return {
        'product_id': product_id,
        'product_name': product_name,
        'pincode': pincode,
        'forecasted_demand': float(adjusted_forecast.mean()) if len(adjusted_forecast) > 0 else 0,
        'peak_forecast_demand': float(adjusted_forecast.max()) if len(adjusted_forecast) > 0 else 0,
        'combined_multiplier': combined_mult,  # ✅ STORE IT
    }

def check_inventory(df_inv, product_id, pincode):
    pincode_wh = {
        560001: ['W1 (North BLR)', 'W2 (South BLR)', 'W3 (Central Hub)'],
        560037: ['W2 (South BLR)', 'W3 (Central Hub)', 'W1 (North BLR)'],
        560064: ['W3 (Central Hub)', 'W1 (North BLR)', 'W2 (South BLR)'],
    }
    
    warehouses = pincode_wh.get(pincode, ['W1 (North BLR)', 'W2 (South BLR)', 'W3 (Central Hub)'])
    inventory = {}
    
    for wh in warehouses:
        stock = df_inv[(df_inv['id'] == product_id) & (df_inv['warehouse'] == wh)]
        inventory[wh] = int(stock.iloc[0]['stock']) if len(stock) > 0 else 0
    
    return {
        'product_id': product_id,
        'inventory': inventory,
        'total': sum(inventory.values()),
        'warehouses': warehouses,
    }

def check_risk(demand_analysis, inventory_status):
    demand = demand_analysis['peak_forecast_demand']
    stock = inventory_status['total']
    
    if demand > 0:
        days = stock / demand
    else:
        days = float('inf')
    
    if stock == 0 or days < 2:
        risk = 'critical'
    elif days < 5:
        risk = 'high'
    elif days < 10:
        risk = 'medium'
    else:
        risk = 'low'
    
    return {
        'product_id': demand_analysis['product_id'],
        'product_name': demand_analysis['product_name'],
        'risk_level': risk,
        'current_stock': stock,
        'days_of_stock': days,
        'needs_reallocation': risk in ['critical', 'high'],
    }

def plan_realloc(risk_analysis, inventory_status, demand_multiplier, order_counter):
    """✅ MULTIPLIER IS APPLIED HERE"""
    if not risk_analysis['needs_reallocation']:
        return None
    
    product_id = risk_analysis['product_id']
    product_name = risk_analysis['product_name']
    demand = risk_analysis['days_of_stock']  # Use days as base for quantity
    
    inv = inventory_status['inventory']
    source_wh = max(inv.items(), key=lambda x: x[1])[0] if inv else None
    
    if not source_wh or inv[source_wh] < demand * 1.5:
        return None
    
    dest_wh = inventory_status['warehouses'][0]
    
    if source_wh == dest_wh:
        return None
    
    # ✅ APPLY MULTIPLIER TO QUANTITY
    quantity = int(demand * demand_multiplier * 2.5)
    
    order_counter[0] += 1
    order = ReallocationOrder(
        order_id=f"Z-{datetime.now().strftime('%d%H%M')}-{order_counter[0]}",
        product_id=product_id,
        product_name=product_name,
        source_warehouse=source_wh,
        destination_warehouse=dest_wh,
        quantity=quantity,
        priority=risk_analysis['risk_level'],
        reason=f"Stock: {risk_analysis['current_stock']}, Days: {risk_analysis['days_of_stock']:.1f}, Multiplier: {demand_multiplier:.2f}x",
        weather_multiplier=demand_multiplier,
        timestamp=datetime.now().isoformat(),
    )
    return order

# === NODES ===

def node_init(state):
    pincode = state['pincode']
    products = get_products(state['demand_data'], pincode)
    state['products_to_check'] = products
    state['analysis_log'] = []
    state['reallocation_orders'] = []
    state['alerts'] = []
    state['status'] = f"Init: {len(products)} products | Weather: {state['weather_label']} | Event: {state['event_label']}"
    return state

def node_analyze(state):
    pincode = state['pincode']
    products = state['products_to_check']
    weather = state['weather_label']
    event = state['event_label']
    
    analysis_log = []
    for p_id in products:
        demand_analysis = analyze_demand(state['demand_data'], int(p_id), pincode, weather, event)
        inventory_status = check_inventory(state['inventory_data'], int(p_id), pincode)
        
        if demand_analysis:
            analysis_log.append({
                'demand_analysis': demand_analysis,
                'inventory_status': inventory_status,
            })
    
    state['analysis_log'] = analysis_log
    state['status'] = f"Analyzed {len(analysis_log)} products"
    return state

def node_risks(state):
    for log in state['analysis_log']:
        demand = log['demand_analysis']
        inv = log['inventory_status']
        
        risk = check_risk(demand, inv)
        
        if risk['needs_reallocation']:
            state['alerts'].append({
                'product_name': risk['product_name'],
                'risk_level': risk['risk_level'],
                'current_stock': risk['current_stock'],
                'days_of_stock': risk['days_of_stock'],
            })
        
        log['risk_analysis'] = risk
    
    state['status'] = f"Risks detected: {len(state['alerts'])} alerts"
    return state

def node_plan(state):
    """✅ THIS IS WHERE MULTIPLIER IS PASSED"""
    order_counter = [0]
    
    for log in state['analysis_log']:
        if 'risk_analysis' not in log:
            continue
        
        risk = log['risk_analysis']
        inv = log['inventory_status']
        demand = log['demand_analysis']
        
        # ✅ GET MULTIPLIER FROM DEMAND ANALYSIS
        multiplier = demand.get('combined_multiplier', 1.0)
        print(f"DEBUG: {demand['product_name']} - Multiplier: {multiplier}")
        
        # ✅ PASS MULTIPLIER TO PLANNING
        order = plan_realloc(risk, inv, multiplier, order_counter)
        if order:
            state['reallocation_orders'].append(asdict(order))
    
    state['status'] = f"Planned {len(state['reallocation_orders'])} orders"
    return state

def node_summary(state):
    state['status'] = f"✅ Complete | {len(state['products_to_check'])} products | {len(state['alerts'])} alerts | {len(state['reallocation_orders'])} orders"
    return state

# === GRAPH ===

def build_graph(df_demand, df_inventory):
    workflow = StateGraph(OptimizationState)
    
    workflow.add_node("init", node_init)
    workflow.add_node("analyze", node_analyze)
    workflow.add_node("risks", node_risks)
    workflow.add_node("plan", node_plan)
    workflow.add_node("summary", node_summary)
    
    workflow.add_edge(START, "init")
    workflow.add_edge("init", "analyze")
    workflow.add_edge("analyze", "risks")
    workflow.add_edge("risks", "plan")
    workflow.add_edge("plan", "summary")
    workflow.add_edge("summary", END)
    
    return workflow.compile()

# === MAIN ===

def run_optimization(pincode, demand_csv, inventory_csv, weather_label="Sunny ☀️", event_label="None"):
    """Execute agent with weather and event"""
    df_d, df_i = load_data(demand_csv, inventory_csv)
    graph = build_graph(df_d, df_i)
    
    state = OptimizationState(
        pincode=pincode,
        weather_label=weather_label,
        event_label=event_label,
        products_to_check=[],
        demand_data=df_d,
        inventory_data=df_i,
        analysis_log=[],
        reallocation_orders=[],
        alerts=[],
        status="Starting...",
    )
    
    result = graph.invoke(state)
    
    return {
        'pincode': result['pincode'],
        'weather': result['weather_label'],
        'event': result['event_label'],
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
    result = run_optimization(
        pincode=560001,
        demand_csv=r"D:\FASHION\data\demand_forecast.csv",
        inventory_csv=r"D:\FASHION\data\warehouse_inventory.csv",
        weather_label="Rainy 🌧️",
        event_label="Diwali 🪔"
    )
    
    print("\n" + "="*70)
    print("ZINTOO AGENTIC OPTIMIZATION")
    print("="*70)
    print(f"Weather: {result['weather']} | Event: {result['event']}")
    print(f"Status: {result['status']}")
    
    if result['reallocation_orders']:
        print(f"\n📦 ORDERS:")
        for order in result['reallocation_orders'][:3]:
            print(f"  {order['product_name']}: {order['quantity']} units (×{order['weather_multiplier']:.2f})")