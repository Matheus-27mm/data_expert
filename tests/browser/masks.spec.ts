import {test,expect} from '@playwright/test';
import {phoneMask,documentMask} from '../../src/inputMasks';
test('contact masks handle paste, partial input and existing formatting',()=>{
 for(const [raw,expected] of [['',''],['11987654321','(11) 98765-4321'],['1134567890','(11) 3456-7890'],['(11) 98765-4321','(11) 98765-4321'],['+55 (11) 98765-4321','+55 (11) 98765-4321'],['5511987654321','(11) 98765-4321'],['+1 212 555 0123','+12125550123'],['11','(11']])expect(phoneMask(raw)).toBe(expected);
 for(const [raw,expected] of [['',''],['12345678900','123.456.789-00'],['12345678000190','12.345.678/0001-90'],['12.345.678/0001-90','12.345.678/0001-90'],['12abc345000190','12.ABC.345/0001-90'],['1234','123.4']])expect(documentMask(raw)).toBe(expected);
});
