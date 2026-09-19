`default_nettype none

module digital_fault_injector #(
    parameter WIDTH = 16
) (
    input  wire [WIDTH-1:0] normal_value,
    input  wire [WIDTH-1:0] force_low_mask,
    input  wire [WIDTH-1:0] force_high_mask,
    input  wire [WIDTH-1:0] safe_value,
    input  wire             force_safe,

    output reg  [WIDTH-1:0] injected_value,
    output wire [WIDTH-1:0] active_fault_mask,
    output wire [WIDTH-1:0] conflict_mask
);

    assign active_fault_mask = force_low_mask | force_high_mask;
    assign conflict_mask = force_low_mask & force_high_mask;

    always @* begin
        if (force_safe)
            injected_value = safe_value;
        else
            injected_value = (normal_value | force_high_mask) &
                             ~force_low_mask;
    end

endmodule

`default_nettype wire
