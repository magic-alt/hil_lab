`default_nettype none

module hil_axi_event_fifo #(
    parameter WIDTH = 16,
    parameter ID_WIDTH = 16,
    parameter DEPTH = 64
) (
    input  wire                    clk,
    input  wire                    rst_n,
    input  wire                    clear,
    input  wire                    push,
    input  wire [63:0]             push_timestamp,
    input  wire [WIDTH-1:0]        push_mask,
    input  wire [WIDTH-1:0]        push_value,
    input  wire [ID_WIDTH-1:0]     push_id,
    input  wire                    pop,
    output wire [63:0]             head_timestamp,
    output wire [WIDTH-1:0]        head_mask,
    output wire [WIDTH-1:0]        head_value,
    output wire [ID_WIDTH-1:0]     head_id,
    output wire                    empty,
    output wire                    full,
    output wire [15:0]             level,
    output reg                     overflow_latched,
    output reg                     order_error_latched
);

    function integer clog2;
        input integer value;
        integer temp;
        begin
            temp = value - 1;
            clog2 = 0;
            while (temp > 0) begin
                clog2 = clog2 + 1;
                temp = temp >> 1;
            end
            if (clog2 < 1)
                clog2 = 1;
        end
    endfunction

    localparam PTR_WIDTH = clog2(DEPTH);

    (* ram_style = "block" *) reg [63:0] timestamp_mem [0:DEPTH-1];
    (* ram_style = "block" *) reg [WIDTH-1:0] mask_mem [0:DEPTH-1];
    (* ram_style = "block" *) reg [WIDTH-1:0] value_mem [0:DEPTH-1];
    (* ram_style = "block" *) reg [ID_WIDTH-1:0] id_mem [0:DEPTH-1];

    reg [PTR_WIDTH-1:0] write_ptr;
    reg [PTR_WIDTH-1:0] read_ptr;
    reg [15:0] count;
    reg [63:0] last_timestamp;

    wire push_order_ok;
    wire accept_push;
    wire accept_pop;

    assign empty = (count == 16'd0);
    assign full = (count >= DEPTH);
    assign level = count;
    assign head_timestamp = empty ? 64'd0 : timestamp_mem[read_ptr];
    assign head_mask = empty ? {WIDTH{1'b0}} : mask_mem[read_ptr];
    assign head_value = empty ? {WIDTH{1'b0}} : value_mem[read_ptr];
    assign head_id = empty ? {ID_WIDTH{1'b0}} : id_mem[read_ptr];

    assign push_order_ok = empty || (push_timestamp >= last_timestamp);
    assign accept_push = push && !full && push_order_ok;
    assign accept_pop = pop && !empty;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            write_ptr <= {PTR_WIDTH{1'b0}};
            read_ptr <= {PTR_WIDTH{1'b0}};
            count <= 16'd0;
            last_timestamp <= 64'd0;
            overflow_latched <= 1'b0;
            order_error_latched <= 1'b0;
        end else if (clear) begin
            write_ptr <= {PTR_WIDTH{1'b0}};
            read_ptr <= {PTR_WIDTH{1'b0}};
            count <= 16'd0;
            last_timestamp <= 64'd0;
            overflow_latched <= 1'b0;
            order_error_latched <= 1'b0;
        end else begin
            if (push) begin
                if (full) begin
                    overflow_latched <= 1'b1;
                end else if (!push_order_ok) begin
                    order_error_latched <= 1'b1;
                end else begin
                    timestamp_mem[write_ptr] <= push_timestamp;
                    mask_mem[write_ptr] <= push_mask;
                    value_mem[write_ptr] <= push_value;
                    id_mem[write_ptr] <= push_id;
                    last_timestamp <= push_timestamp;
                    if (write_ptr == (DEPTH - 1))
                        write_ptr <= {PTR_WIDTH{1'b0}};
                    else
                        write_ptr <= write_ptr + {{(PTR_WIDTH-1){1'b0}}, 1'b1};
                end
            end

            if (accept_pop) begin
                if (read_ptr == (DEPTH - 1))
                    read_ptr <= {PTR_WIDTH{1'b0}};
                else
                    read_ptr <= read_ptr + {{(PTR_WIDTH-1){1'b0}}, 1'b1};
                if (!accept_push && (count == 16'd1))
                    last_timestamp <= 64'd0;
            end

            case ({accept_push, accept_pop})
                2'b10: count <= count + 16'd1;
                2'b01: count <= count - 16'd1;
                default: count <= count;
            endcase
        end
    end

endmodule

`default_nettype wire
