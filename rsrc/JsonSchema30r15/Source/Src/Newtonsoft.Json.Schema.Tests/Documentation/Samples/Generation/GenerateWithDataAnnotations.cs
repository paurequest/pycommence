﻿#region License
// Copyright (c) Newtonsoft. All Rights Reserved.
// License: https://raw.github.com/JamesNK/Newtonsoft.Json.Schema/master/LICENSE.md
#endregion

#if !(NET35 || NET40)
using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.Linq;
using System.Text;
using Newtonsoft.Json.Schema.Generation;
using Newtonsoft.Json.Serialization;
#if DNXCORE50
using Xunit;
using Test = Xunit.FactAttribute;
using Assert = Newtonsoft.Json.Schema.Tests.XUnitAssert;
#else
using NUnit.Framework;
#endif

namespace Newtonsoft.Json.Schema.Tests.Documentation.Samples.Generation
{
    [TestFixture]
    public class GenerateWithDataAnnotations : TestFixtureBase
    {
        #region Types
        public class Building
        {
            [Required]
            [MaxLength(100)]
            public string Name { get; set; }

            [Required]
            [Phone]
            public string PhoneNumber { get; set; }

            [Required]
            [EnumDataType(typeof(BuildingZone))]
            public string Zone { get; set; }
        }

        public enum BuildingZone
        {
            Residential,
            Commercial,
            Industrial
        }
        #endregion

        [Test]
        public void Example()
        {
            #region Usage
            JSchemaGenerator generator = new JSchemaGenerator();

            JSchema schema = generator.Generate(typeof(Building));
            // {
            //   "type": "object",
            //   "properties": {
            //     "Name": {
            //       "type": "string",
            //       "maxLength": 100
            //     },
            //     "PhoneNumber": {
            //       "type": "string",
            //       "format": "phone"
            //     },
            //     "Zone": {
            //       "type": "string",
            //       "enum": [
            //         "Residential",
            //         "Commercial",
            //         "Industrial"
            //       ]
            //     }
            //   },
            //   "required": [
            //     "Name",
            //     "PhoneNumber",
            //     "Zone"
            //   ]
            // }
            #endregion

            Assert.AreEqual(JSchemaType.Object, schema.Type);
        }
    }
}

#endif