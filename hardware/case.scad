/* =====================================================================
   DESK HELPER — v6
   Closed box + lid. Screen mounts on top, separately.
   ---------------------------------------------------------------------
   WHAT CHANGED FROM v5
     - screen holder removed entirely; you build that on top of the lid
     - box walls raised so the lid clears the Pico and the jumper wires
     - removable lid with a locating lip
     - cable pass-through in the lid for the screen wires
     - USB cutout added — needed now that the walls are taller than
       the Pico's socket

   STILL BUILT AROUND YOUR STLs
     Button: cap / stem / guide / mount. The 24.89 mm mount disc drops
     into a counterbore in the front shelf and finishes flush. Cap ends
     up 9.4 mm above the shelf.

   HOLDING THE WIRES ON, WITHOUT SOLDER OR HOT GLUE
     Under each button the shelf floor has three slots. The single
     narrow one is a friction clamp: push the jumper wire into it and
     it grips by itself. The pair behind take a zip tie if you have
     one. Either way the wire is anchored ~10 mm downstream of the
     connector, so tugging the cable never levers the connector off
     the switch leg. That is what actually keeps it attached.

     Do NOT superglue near the switch. It wicks along stranded wire
     and into seams, and the stem has to slide freely just above.

   >>> CHECK usb_side BEFORE PRINTING <<<
   Look down at the tray with the buttons nearest you. If the Pico's
   USB socket points right, leave usb_side = 1. If left, set it to -1.
   ===================================================================== */

part = "all";     // "coupon" | "lid" | "tray" | "spacer" | "all"

/* ---------- FROM YOUR BUTTON STLs — already measured ---------------- */
mount_d    = 24.89;  // diameter of the mount disc
mount_t    = 1.80;   // thickness of the disc
mount_boss = [22.0, 16.0]; // slot below the disc. Yours arrive with
                           //   the tactile switch already fitted, and the
                           //   Dupont connectors on the legs splay out
                           //   wider than the switch body itself. This
                           //   cavity is fully hidden under the shelf, so
                           //   it costs nothing to leave it generous.

/* ---------- BREADBOARD ---------------------------------------------- */
bb_len     = 83.0;
bb_wid     = 55.0;
bb_h       = 9.5;    // INCLUDING adhesive backing

/* ---------- HEIGHT --------------------------------------------------- */
headroom   = 20.0;   // clear space above the breadboard surface.
                     //   A male Dupont housing stands ~11 mm proud and
                     //   the wire bends over above that. Lower this to
                     //   16 for a squatter box if your wiring is flat.

/* ---------- USB ------------------------------------------------------ */
usb_side   = 1;      // 1 = right wall, -1 = left wall
usb_w      = 15.0;   // opening width
usb_z0     = 10.5;   // bottom of the opening, above the floor
usb_z1     = 21.0;   // top. The socket itself only reaches ~17.4,
                     //   but a micro-USB plug's moulding is taller than
                     //   the socket, so the opening has to clear that
                     //   rather than just the connector.

/* ---------- LID ------------------------------------------------------ */
lid_t      = 2.5;
lid_lip    = 3.0;    // depth of the locating lip
lid_clr    = 0.4;    // clearance so it lifts off easily
cable_w    = 20.0;   // pass-through for the screen wires
cable_d    = 10.0;
cable_back = 14.0;   // its centre, measured in from the back wall

/* ---------- SPACER COLLAR -------------------------------------------- */
spacer_h   = 15.0;   // how much height it adds. 10-20 all work.
ledge_t    = 2.0;    // ledge the lid's lip lands on
sp_lipw    = 2.0;    // wall of the locating lip underneath

/* ---------- BUZZER --------------------------------------------------- */
buz_bay    = false;  // true = adds an open bay at the back,
                     //   which makes the box 28 mm deeper
buz_w      = 24.0;   // CONFIRM WITH CALIPERS
buz_d      = 20.0;
buz_wall   = 1.6;
buz_lip    = 6.0;
buz_clr    = 0.8;

/* ---------- FITS ----------------------------------------------------- */
mount_clr  = 0.5;    // clearance on the mount disc; it should drop in
fit        = 1.0;    // clearance per side around the breadboard.
                     //   Nominal half-size boards are 83 x 55 but they
                     //   vary, and moulding flash adds a little. At 1.0
                     //   the pocket is 85 x 57, which swallows anything
                     //   in that class. The adhesive backing stops it
                     //   sliding, so a loose pocket costs you nothing.
wall       = 2.2;
floor_t    = 2.0;

/* ---------- BUTTON SHELF --------------------------------------------- */
btn_count  = 2;
btn_gap    = 32.0;   // centre to centre; must exceed mount_d
tie_slot   = [8.0, 2.6];   // zip-tie slots for wire strain relief
tie_dy     = [7, 12];      // their offsets behind the button centre
pinch_slot = [12.0, 1.3];  // friction slot — press a jumper wire into
                           //   this and it grips on its own, no tie and
                           //   no glue needed. 1.3 suits ~1.6 mm jumper
                           //   wire; widen to 1.5 if it will not go in.
pinch_dy   = -9;           // in front of the button centre
shelf_d    = 32.0;
shelf_top  = 20.0;
shelf_t    = 8.0;
$fn        = 72;

/* ---------- DERIVED --------------------------------------------------- */
mount_bore  = mount_d + mount_clr;
shelf_bot   = shelf_top - shelf_t;

pocket_l    = bb_len + 2*fit;
pocket_w    = bb_wid + 2*fit;

Z           = floor_t + bb_h + headroom;   // top of the box walls

y_front     = shelf_d;                     // box starts here
y_pocket    = y_front + wall;
y_backwall  = y_pocket + pocket_w;
y_boxback   = y_backwall + wall;
box_d       = y_boxback - y_front;

X = pocket_l + 2*wall;

bay_w       = buz_d + buz_clr + 2*buz_wall;   // module turned 90 deg
bay_d       = buz_w + buz_clr + 2*buz_wall;
Y = buz_bay ? y_boxback + bay_d : y_boxback;

btn_x = [ for (i = [0:btn_count-1])
          X/2 + (i - (btn_count-1)/2) * btn_gap ];

assert(btn_gap > mount_d + 3, "Caps will collide — raise btn_gap.");
assert(shelf_d > mount_d + 5, "Shelf too shallow for the caps.");
assert(shelf_t > mount_t + 2, "Shelf too thin for the counterbore.");
assert(usb_z1 < Z, "USB opening is taller than the wall.");
assert(cable_back > cable_d/2 + 2, "Cable slot runs into the back wall.");

echo(str("Footprint:    ", X, " x ", Y, " mm"));
echo(str("Board pocket: ", pocket_l, " x ", pocket_w,
         " mm (board assumed ", bb_len, " x ", bb_wid, ")"));
echo(str("Box walls:    ", Z, " mm; with lid ", Z + lid_t, " mm"));
echo(str("Caps reach:   ", shelf_top + 9.4, " mm"));
echo(str("Headroom above breadboard: ", headroom, " mm"));
echo(str("With spacer: ", Z + spacer_h + lid_t, " mm total, ",
         headroom + spacer_h, " mm of wire room"));
echo(str("USB opening on the ", usb_side > 0 ? "RIGHT" : "LEFT", " wall"));

/* ===================================================================== */

// Counterbore for the mount disc, plus a slot for everything below it.
module mount_recess(x, y) {
    translate([x, y, shelf_top - mount_t])
        cylinder(h = mount_t + 0.2, d = mount_bore);
    translate([x - mount_boss[0]/2, y - mount_boss[1]/2, shelf_bot - 1])
        cube([mount_boss[0], mount_boss[1], shelf_t - mount_t + 1.2]);
}

module button_shelf() {
    difference() {
        cube([X, shelf_d, shelf_top]);
        // hollow underneath, open at the back into the box
        translate([wall, wall, floor_t])
            cube([X - 2*wall, shelf_d - wall + 0.1, shelf_bot - floor_t]);
        for (x = btn_x) mount_recess(x, shelf_d/2);
        // strain relief: thread a zip tie down one slot and up the other
        // to clamp each button's wires against the shelf floor
        for (x = btn_x) {
            for (dy = tie_dy)
                translate([x - tie_slot[0]/2,
                           shelf_d/2 + dy - tie_slot[1]/2, -1])
                    cube([tie_slot[0], tie_slot[1], floor_t + 2]);
            // friction slot: push the wire in, it holds itself
            translate([x - pinch_slot[0]/2,
                       shelf_d/2 + pinch_dy - pinch_slot[1]/2, -1])
                cube([pinch_slot[0], pinch_slot[1], floor_t + 2]);
        }
    }
}

module box() {
    difference() {
        translate([0, y_front, 0]) cube([X, box_d, Z]);
        // breadboard pocket, open all the way to the top
        translate([wall, y_pocket, floor_t])
            cube([pocket_l, pocket_w, Z]);
        // floor window, saves material
        translate([wall + 6, y_pocket + 6, -1])
            cube([pocket_l - 12, pocket_w - 12, floor_t + 2]);
        // wire window through the front wall, into the shelf cavity
        translate([X/2 - 30, y_front - 0.5, floor_t + 1])
            cube([60, wall + 1, shelf_bot - floor_t - 2]);
        // USB opening
        translate([usb_side > 0 ? X - wall - 0.5 : -0.5,
                   y_pocket + pocket_w/2 - usb_w/2, usb_z0])
            cube([wall + 1, usb_w, usb_z1 - usb_z0]);
        // cable notches in the back wall, for the buzzer lead
        for (x = [X/4, 3*X/4])
            translate([x - 4.5, y_backwall - 0.5, floor_t + bb_h - 2])
                cube([9, wall + 1, 10]);
    }
}

// Open bay behind the box. Module lies flat, sound facing up.
module buzzer_bay() {
    difference() {
        translate([wall, y_boxback, 0]) cube([bay_w, bay_d, buz_lip]);
        translate([wall + buz_wall, y_boxback + buz_wall, floor_t])
            cube([buz_d + buz_clr, buz_w + buz_clr, buz_lip]);
        // notch for the JST lead, facing the box
        translate([wall + bay_w/2 - 4, y_boxback - 0.5, floor_t + 1])
            cube([8, buz_wall + 1, buz_lip]);
    }
}

module tray() {
    union() {
        button_shelf();
        box();
        if (buz_bay) buzzer_bay();
    }
}

/* ---- LID -------------------------------------------------------------
   Prints flat, lip upwards, no supports. Sits on the box walls and
   locates on the lip. Lift it off by the cable slot.
   --------------------------------------------------------------------- */
module lid() {
    cy = y_backwall - cable_back;      // centre of the cable slot
    difference() {
        union() {
            translate([0, y_front, 0]) cube([X, box_d, lid_t]);
            // locating lip, drops into the breadboard opening
            translate([wall + lid_clr, y_pocket + lid_clr, -lid_lip])
                cube([pocket_l - 2*lid_clr, pocket_w - 2*lid_clr, lid_lip]);
        }
        // cable pass-through, rounded ends
        hull() for (s = [-1, 1])
            translate([X/2 + s*(cable_w - cable_d)/2, cy, -lid_lip - 1])
                cylinder(h = lid_t + lid_lip + 2, d = cable_d);
        // finger notch at the front edge, to lift it off
        translate([X/2, y_front - 0.1, -lid_lip - 1])
            cylinder(h = lid_t + lid_lip + 2, d = 16);
    }
}

/* ---- SPACER COLLAR ---------------------------------------------------
   Goes between the tray and the lid to make room for the wiring.
   Its lip drops into the box the same way the lid's did, and its own
   opening then accepts the lid's lip — so the existing lid still
   locates properly and nothing else needs reprinting.
   Print it lip-down, as oriented. No supports.
   --------------------------------------------------------------------- */
module spacer() {
    pl2 = pocket_l - 2*lid_clr;
    pw2 = pocket_w - 2*lid_clr;
    difference() {
        union() {
            translate([0, y_front, 0]) cube([X, box_d, spacer_h]);
            // locating lip, drops into the box opening
            translate([wall + lid_clr, y_pocket + lid_clr, -lid_lip])
                cube([pl2, pw2, lid_lip]);
        }
        // socket above the ledge, takes the lid's lip
        translate([wall, y_pocket, ledge_t])
            cube([pocket_l, pocket_w, spacer_h]);
        // wire opening straight through
        translate([wall + lid_clr + sp_lipw,
                   y_pocket + lid_clr + sp_lipw, -lid_lip - 1])
            cube([pl2 - 2*sp_lipw, pw2 - 2*sp_lipw,
                  spacer_h + lid_lip + 2]);
    }
}

// One mount station. Print this to check the disc drops in flush.
module coupon() {
    difference() {
        translate([X/2 - 17, shelf_d/2 - 17, 0]) cube([34, 34, shelf_top]);
        mount_recess(X/2, shelf_d/2);
        translate([X/2 - 14, shelf_d/2 - 14, -1])
            cube([28, 28, shelf_bot + 1]);
    }
}

/* ---- OUTPUT ---------------------------------------------------------- */
if (part == "tray")   tray();
if (part == "lid")    translate([0, -y_front, lid_lip]) lid();
if (part == "coupon") coupon();
if (part == "spacer") translate([0, -y_front, lid_lip]) spacer();
if (part == "all") {
    tray();
    translate([X + 12, 0, lid_lip]) lid();
    translate([-X/2 + 17 - 40, shelf_d/2 - 17 + 40, 0]) coupon();
}
