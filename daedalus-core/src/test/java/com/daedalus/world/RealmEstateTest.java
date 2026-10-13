package com.daedalus.world;

import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class RealmEstateTest {
    private List<RealmEstate.PlacedLand> square(int side) {
        var out=new ArrayList<RealmEstate.PlacedLand>();
        for(int z=0;z<side;z++) for(int x=0;x<side;x++)
            out.add(new RealmEstate.PlacedLand(z*side+x,new RealmLandGrid.Cell(-49+x,-49+z)));
        return out;
    }
    @Test void bundleKeepsExistingIdsAndCurrentPlacement() {
        for(int side=2;side<=10;side++) {
            var input=square(side);java.util.Collections.reverse(input);
            var estate=new RealmEstate("world-zero",input);
            assertEquals(side,estate.side());assertEquals(0,estate.district());
            assertEquals(side*side,estate.landNumbers().size());
            assertEquals(0,estate.landNumbers().getFirst());
            // ID 0's default is (0,0); a moved land's explicit placement must win.
            assertEquals(new RealmLandGrid.Cell(-49,-49),estate.lands().getFirst().cell());
            input.clear();assertEquals(side*side,estate.lands().size());
            assertThrows(UnsupportedOperationException.class,()->estate.lands().clear());
        }
    }
    @Test void rejectsDuplicatesHolesAndDistrictCrossing() {
        var duplicateId=square(2);duplicateId.set(1,new RealmEstate.PlacedLand(0,duplicateId.get(1).cell()));
        assertThrows(IllegalArgumentException.class,()->new RealmEstate("world-zero",duplicateId));
        var duplicateCell=square(2);duplicateCell.set(1,new RealmEstate.PlacedLand(1,duplicateCell.getFirst().cell()));
        assertThrows(IllegalArgumentException.class,()->new RealmEstate("world-zero",duplicateCell));
        var hole=square(2);hole.set(3,new RealmEstate.PlacedLand(3,new RealmLandGrid.Cell(-47,-48)));
        assertThrows(IllegalArgumentException.class,()->new RealmEstate("world-zero",hole));
        var split=square(2).stream().map(p->new RealmEstate.PlacedLand(p.number(),new RealmLandGrid.Cell(p.cell().x()+9,p.cell().z()))).toList();
        assertThrows(IllegalArgumentException.class,()->new RealmEstate("world-zero",split));
        assertThrows(IllegalArgumentException.class,()->new RealmEstate("world-zero",square(1)));
        assertThrows(IllegalArgumentException.class,()->new RealmEstate("Bad realm",square(2)));
        assertThrows(IllegalArgumentException.class,()->new RealmEstate.PlacedLand(10000,new RealmLandGrid.Cell(0,0)));
        assertThrows(IllegalArgumentException.class,()->new RealmEstate.PlacedLand(-1,new RealmLandGrid.Cell(0,0)));
    }
}
