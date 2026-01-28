"""
Basic FlowForge workflow example.

This example demonstrates:
- Defining a workflow function with @flowforge.function
- Using step.run() for memoized step execution
- Using step.sleep() for delays
- Using step.ai() for LLM calls (simulated in dev mode)

Run this example with:
    cd examples
    flowforge dev .

Then send an event:
    flowforge send order/created -d '{"order_id": "123", "customer": "Alice", "total": 99.99}'
"""

from flowforge import FlowForge, Context, step

# Initialize FlowForge client
flowforge = FlowForge(app_id="example-app")


# Helper functions that represent your business logic
async def validate_order(order: dict) -> dict:
    """Validate order data."""
    print(f"  Validating order {order.get('order_id')}...")
    # Simulate validation
    if order.get("total", 0) <= 0:
        raise ValueError("Order total must be positive")
    return {"valid": True, "order_id": order.get("order_id")}


async def process_payment(amount: float, order_id: str) -> dict:
    """Process payment for an order."""
    print(f"  Processing payment of ${amount} for order {order_id}...")
    # Simulate payment processing
    return {
        "success": True,
        "transaction_id": f"txn_{order_id}",
        "amount": amount,
    }


async def send_confirmation_email(customer: str, order_id: str) -> dict:
    """Send order confirmation email."""
    print(f"  Sending confirmation email to {customer}...")
    return {"sent": True, "to": customer, "order_id": order_id}


# Define the workflow function
@flowforge.function(
    id="process-order",
    trigger=flowforge.trigger.event("order/created"),
    retries=3,
    timeout="10m",
)
async def process_order(ctx: Context) -> dict:
    """
    Process a new order through multiple steps.

    This workflow:
    1. Validates the order
    2. Checks for fraud using AI
    3. Processes the payment
    4. Waits 5 seconds (simulating a delay)
    5. Sends confirmation email

    Each step is memoized - if the function restarts,
    completed steps won't be re-executed.
    """
    order = ctx.event.data
    ctx.log(f"Processing order {order.get('order_id')}")

    # Step 1: Validate the order
    validation = await step.run(
        "validate-order",
        validate_order,
        order,
    )
    ctx.log(f"Order validated: {validation}")

    # Step 2: AI-powered fraud check
    fraud_check = await step.ai(
        "fraud-check",
        model="gpt-4o",
        prompt=f"""Analyze this order for fraud indicators:
        Order ID: {order.get('order_id')}
        Customer: {order.get('customer')}
        Total: ${order.get('total')}

        Respond with JSON: {{"risk_score": 0.0-1.0, "reason": "..."}}
        """,
    )
    ctx.log(f"Fraud check result: {fraud_check}")

    # Step 3: Process payment
    payment = await step.run(
        "process-payment",
        process_payment,
        order.get("total", 0),
        order.get("order_id"),
    )
    ctx.log(f"Payment processed: {payment}")

    # Step 4: Wait before sending email (to demonstrate sleep)
    await step.sleep("pre-email-delay", "5s")

    # Step 5: Send confirmation email
    confirmation = await step.run(
        "send-confirmation",
        send_confirmation_email,
        order.get("customer", "customer@example.com"),
        order.get("order_id"),
    )
    ctx.log(f"Confirmation sent: {confirmation}")

    return {
        "status": "completed",
        "order_id": order.get("order_id"),
        "transaction_id": payment.get("transaction_id"),
    }


# Simple hello world example
@flowforge.function(
    id="hello-world",
    trigger=flowforge.trigger.event("test/hello"),
)
async def hello_world(ctx: Context) -> dict:
    """Simple hello world function."""
    name = ctx.event.data.get("name", "World")
    return {"message": f"Hello, {name}!"}


if __name__ == "__main__":
    # For local development, you can start the server directly
    flowforge.serve(
        functions=[process_order, hello_world],
        host="0.0.0.0",
        port=8080,
    )
